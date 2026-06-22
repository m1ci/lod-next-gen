#!/usr/bin/env python3

import argparse
import json
import os
import sys
import requests


# =========================================================
# CONSTANTS
# =========================================================
SOURCE_GROUP = "https://databus.dev.dbpedia.link/fhofer/dbpedia-wikipedia-kg-dump"

SPARQL_ENDPOINT = "https://databus.dev.dbpedia.link/sparql"

PUBLISH_URL = "https://databus.dbpedia.org/api/publish?fetch-file-properties=false"

TARGET_BASE = "https://databus.dbpedia.org/knowledge-graph-catalog"


# =========================================================
# DEBUG
# =========================================================
def debug(title, obj):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def mask(headers):
    h = dict(headers)
    if "X-API-KEY" in h:
        h["X-API-KEY"] = "***REDACTED***"
    return h


# =========================================================
# JSON-LD CORE FIX (IMPORTANT)
# =========================================================
def all_nodes(data):
    if isinstance(data, dict):
        g = data.get("@graph")

        if isinstance(g, list):
            return g
        if isinstance(g, dict):
            return [g]

        return [data]

    return []


def find_first(data, ttype):
    for n in all_nodes(data):
        t = n.get("@type")

        if t == ttype:
            return n

        if isinstance(t, list) and ttype in t:
            return n

    return None


def find_all(data, ttype):
    out = []

    for n in all_nodes(data):
        t = n.get("@type")

        if t == ttype:
            out.append(n)

        elif isinstance(t, list) and ttype in t:
            out.append(n)

    return out


# =========================================================
# HTTP
# =========================================================
def fetch_jsonld(url):
    headers = {"accept": "application/ld+json"}

    debug("GET", {"url": url, "headers": headers})

    r = requests.get(url, headers=headers)

    print("→ STATUS:", r.status_code)

    if r.status_code >= 400:
        print("❌ RESPONSE:", r.text)

    r.raise_for_status()
    return r.json()


def publish(payload, api_key):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/ld+json",
        "X-API-KEY": api_key.strip()
    }

    debug("POST PUBLISH", {
        "url": PUBLISH_URL,
        "headers": mask(headers),
        "payload": payload
    })

    r = requests.post(PUBLISH_URL, headers=headers, json=payload)

    print("→ STATUS:", r.status_code)

    if r.status_code >= 400:
        print("❌ RESPONSE:", r.text)
        sys.exit(1)

    return r.json()


# =========================================================
# GROUP
# =========================================================
def fetch_group():
    data = fetch_jsonld(SOURCE_GROUP)

    g = find_first(data, "Group")

    if not g:
        raise Exception("Group node not found")

    return (
        g.get("description", ""),
        g.get("abstract", "")
    )


def publish_group(group_id, title, description, abstract, api_key):
    group_id = group_id.strip("/")

    payload = {
        "@context": "https://databus.dbpedia.org/res/context.jsonld",
        "@graph": {
            "@type": "Group",
            "@id": f"{TARGET_BASE}/{group_id}",
            "title": title,
            "description": description,
            "abstract": abstract
        }
    }

    print("\n===== PUBLISH GROUP =====")
    publish(payload, api_key)


# =========================================================
# ARTIFACTS
# =========================================================
def query_artifacts():
    query = f"""
PREFIX databus: <https://dataid.dbpedia.org/databus#>

SELECT DISTINCT ?artifact
WHERE {{
  ?version databus:group <{SOURCE_GROUP}> .
  ?version databus:artifact ?artifact .
}}
"""

    debug("SPARQL ARTIFACTS", {"query": query})

    r = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers={"accept": "application/sparql-results+json"}
    )

    print("→ STATUS:", r.status_code)

    if r.status_code >= 400:
        print("❌ RESPONSE:", r.text)
        r.raise_for_status()

    data = r.json()

    return [
        b["artifact"]["value"]
        for b in data["results"]["bindings"]
    ]


def publish_artifact(group_id, artifact_uri, api_key):
    data = fetch_jsonld(artifact_uri)

    a = find_first(data, "Artifact")

    if not a:
        raise Exception(f"Artifact node missing: {artifact_uri}")

    artifact_id = artifact_uri.rstrip("/").split("/")[-1]

    target_id = f"{TARGET_BASE}/{group_id}/{artifact_id}"

    payload = {
        "@context": "https://databus.dbpedia.org/res/context.jsonld",
        "@graph": {
            "@type": "Artifact",
            "@id": target_id,
            "title": a.get("title", artifact_id),
            "description": a.get("description", ""),
            "abstract": a.get("abstract", "")
        }
    }

    print("\n===== PUBLISH ARTIFACT =====", target_id)
    publish(payload, api_key)


# =========================================================
# VERSIONS
# =========================================================
def query_versions(artifact_uri):
    query = f"""
PREFIX databus: <https://dataid.dbpedia.org/databus#>

SELECT DISTINCT ?version
WHERE {{
  ?version databus:group <{SOURCE_GROUP}> .
  ?version databus:artifact <{artifact_uri}> .
}}
"""

    debug("SPARQL VERSIONS", {"query": query})

    r = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers={"accept": "application/sparql-results+json"}
    )

    print("→ STATUS:", r.status_code)

    if r.status_code >= 400:
        print("❌ RESPONSE:", r.text)
        r.raise_for_status()

    data = r.json()

    return [
        b["version"]["value"]
        for b in data["results"]["bindings"]
    ]


# =========================================================
# VERSION + PARTS
# =========================================================
def publish_version(group_id, artifact_id, version_uri, api_key):

    data = fetch_jsonld(version_uri)

    v = find_first(data, "Version")
    parts = find_all(data, "Part")

    if not v:
        raise Exception(f"Version node missing: {version_uri}")

    version_number = (
        v.get("hasVersion")
        or version_uri.rstrip("/").split("/")[-1]
    )

    version_id = f"{TARGET_BASE}/{group_id}/{artifact_id}/{version_number}"

    distributions = []

    for p in parts:

        part_id = p["@id"]

        fragment = part_id.split("#", 1)[1] if "#" in part_id else ""

        target_part_id = (
            f"{version_id}#{fragment}"
            if fragment
            else part_id
        )

        dist = {
            "@id": target_part_id,
            "@type": "Part",
            "downloadURL": p.get("downloadURL"),
            "sha256sum": p.get("sha256sum"),
            "dcat:byteSize": p.get("dcat:byteSize")
        }

        # =====================================================
        # ✅ CRITICAL FIX: COPY CONTENT VARIANTS
        # =====================================================
        if p.get("dcv:graph") is not None:
            dist["dcv:graph"] = p.get("dcv:graph")

        if p.get("dcv:partition") is not None:
            dist["dcv:partition"] = p.get("dcv:partition")
    
        if "compression" in p:
            dist["compression"] = p["compression"]

        if "formatExtension" in p:
            dist["formatExtension"] = p["formatExtension"]

        distributions.append(dist)

    payload = {
        "@context": "https://databus.dbpedia.org/res/context.jsonld",
        "@graph": {
            "@type": "Version",
            "@id": version_id,
            "title": v.get("title", artifact_id),
            "description": v.get("description", ""),
            "abstract": v.get("abstract", ""),
            "license": v.get("license"),
            "distribution": distributions
        }
    }

    print("\n===== PUBLISH VERSION =====", version_id)
    publish(payload, api_key)


# =========================================================
# MAIN
# =========================================================
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("group_id")
    parser.add_argument("group_title")
    parser.add_argument("--api-key", required=False)

    args = parser.parse_args()

    api_key = args.api_key or os.getenv("DATABUS_API_KEY")

    if not api_key:
        print("Missing API key")
        sys.exit(1)

    # ---------------- GROUP ----------------
    print("\n################ GROUP ################")

    desc, abs_ = fetch_group()

    publish_group(args.group_id, args.group_title, desc, abs_, api_key)

    # ---------------- ARTIFACTS ----------------
    print("\n################ ARTIFACTS ################")

    artifacts = query_artifacts()

    print(f"\nFOUND {len(artifacts)} ARTIFACTS")

    for artifact_uri in artifacts:

        try:
            print("\n======================================")

            publish_artifact(args.group_id, artifact_uri, api_key)

            artifact_id = artifact_uri.rstrip("/").split("/")[-1]

            versions = query_versions(artifact_uri)

            print(f"FOUND {len(versions)} VERSIONS")

            for v in versions:
                publish_version(
                    args.group_id,
                    artifact_id,
                    v,
                    api_key
                )

        except Exception as e:
            print("❌ FAILED:", artifact_uri)
            print(e)


if __name__ == "__main__":
    main()