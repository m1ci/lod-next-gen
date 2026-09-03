#!/usr/bin/env python3
"""Add the next frozen SSTIM release to the KG Catalog metadata.

Stable Git tags are the discovery surface. A tag is not accepted on its own:
the corresponding W3C-CG snapshot manifest and whole-set namespace artifact
must both be published, the manifest must identify the same released version,
and the Turtle must carry that version and one unambiguous issue date.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import requests
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
YAML_FILE = Path(os.environ.get("SSTIM_METADATA_FILE", SCRIPT_DIR / "metadata.yaml"))

TAGS_API = "https://api.github.com/repos/w3c-cg/sstim/tags"
PUBLICATION_BASE = "https://w3c-cg.github.io/sstim/ontology"
CONCEPT_DOI = "10.5281/zenodo.21286974"
TIMEOUT = 30

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TITLE_VERSION_PATTERN = re.compile(r"^SSTIM (\d+\.\d+\.\d+)$")
URL_VERSION_PATTERN = re.compile(r"/ontology/(\d+\.\d+\.\d+)/sstim-namespace\.ttl$")
ISSUED_PATTERN = re.compile(r'dct:issued\s+"(\d{4}-\d{2}-\d{2})"\^\^xsd:date')
VERSION_INFO_PATTERN = re.compile(r'owl:versionInfo\s+"([^"]+)"')

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "dbpedia-kg-catalog-sstim-release-check/1.0",
}


def semantic_version(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"not a stable semantic version: {value!r}")
    return tuple(int(part) for part in match.groups())


def load_metadata() -> dict:
    with YAML_FILE.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{YAML_FILE} does not contain a metadata mapping")
    return data


def save_metadata(data: dict) -> None:
    with YAML_FILE.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)


def sstim_artifact(data: dict) -> dict:
    artifacts = [
        artifact
        for artifact in data.get("artifacts", [])
        if artifact.get("artifact") == "sstim"
    ]
    if len(artifacts) != 1:
        raise ValueError(f"expected exactly one SSTIM artifact, found {len(artifacts)}")
    return artifacts[0]


def catalogued_versions(artifact: dict) -> set[str]:
    versions: set[str] = set()
    for entry in artifact.get("versions", []):
        title_match = TITLE_VERSION_PATTERN.fullmatch(str(entry.get("title", "")))
        if title_match:
            versions.add(title_match.group(1))
            continue
        for distribution in entry.get("distributions", []):
            url_match = URL_VERSION_PATTERN.search(str(distribution.get("file", "")))
            if url_match:
                versions.add(url_match.group(1))
                break
    if not versions:
        raise ValueError("could not derive any catalogued SSTIM semantic version")
    return versions


def available_versions(session=requests) -> list[str]:
    response = session.get(
        TAGS_API,
        params={"per_page": 100},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    releases = []
    for tag in response.json():
        match = TAG_PATTERN.fullmatch(str(tag.get("name", "")))
        if match:
            releases.append(".".join(match.groups()))
    return sorted(set(releases), key=semantic_version)


def next_version(available: list[str], catalogued: set[str]) -> str | None:
    newest_catalogued = max(catalogued, key=semantic_version)
    newer = [
        version
        for version in available
        if semantic_version(version) > semantic_version(newest_catalogued)
        and version not in catalogued
    ]
    return min(newer, key=semantic_version) if newer else None


def fetch_release(version: str, session=requests) -> dict:
    manifest_url = f"{PUBLICATION_BASE}/{version}/manifest.json"
    manifest_response = session.get(manifest_url, timeout=TIMEOUT)
    manifest_response.raise_for_status()
    manifest = manifest_response.json()
    suite = manifest.get("suite", {})
    if suite.get("version") != version or suite.get("status") != "released":
        raise ValueError(
            f"{manifest_url} is not the released SSTIM {version} manifest"
        )
    if not manifest.get("immutableRelease"):
        raise ValueError(f"{manifest_url} does not declare an immutable release")

    artifact_url = f"{PUBLICATION_BASE}/{version}/sstim-namespace.ttl"
    artifact_response = session.get(artifact_url, timeout=TIMEOUT)
    artifact_response.raise_for_status()
    content = artifact_response.content
    if not content:
        raise ValueError(f"{artifact_url} is empty")
    text = content.decode("utf-8")

    declared_versions = set(VERSION_INFO_PATTERN.findall(text))
    if version not in declared_versions:
        raise ValueError(f"{artifact_url} does not declare owl:versionInfo {version}")

    issued_dates = set(ISSUED_PATTERN.findall(text))
    if len(issued_dates) != 1:
        raise ValueError(
            f"{artifact_url} has {len(issued_dates)} distinct dct:issued dates"
        )

    return {
        "version": version,
        "issued": issued_dates.pop(),
        "url": artifact_url,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def catalog_version_key(release: dict, artifact: dict) -> str:
    date_key = release["issued"].replace("-", ".")
    used = {str(entry.get("version")) for entry in artifact.get("versions", [])}
    if date_key not in used:
        return date_key
    # SSTIM occasionally releases rapidly. Keep a date-shaped Databus version
    # while making two releases issued on the same day unambiguous.
    return f"{date_key}.{release['version']}"


def create_version_entry(release: dict, artifact: dict) -> dict:
    version = release["version"]
    return {
        "version": catalog_version_key(release, artifact),
        "title": f"SSTIM {version}",
        "abstract": f"Release {version} of the Sensory Stimulation Ontology.",
        "description": (
            f"Frozen whole-set namespace document for SSTIM {version}. "
            "The release is byte-stable under its version IRI and archived on "
            f"Zenodo under concept DOI {CONCEPT_DOI}. This catalog entry was "
            "discovered from the canonical W3C-CG release tag and accepted only "
            "after its published immutable manifest and ontology version agreed."
        ),
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "distributions": [
            {
                "file": release["url"],
                "format": "ttl",
                "status": "pending",
                "sha256": release["sha256"],
                "size": release["size"],
            }
        ],
    }


def main() -> None:
    data = load_metadata()
    artifact = sstim_artifact(data)
    catalogued = catalogued_versions(artifact)
    version = next_version(available_versions(), catalogued)
    if version is None:
        print(f"SSTIM KG metadata is current at {max(catalogued, key=semantic_version)}.")
        return

    release = fetch_release(version)
    artifact.setdefault("versions", []).append(create_version_entry(release, artifact))
    save_metadata(data)
    print(
        f"Added SSTIM {version}: {release['size']} bytes, "
        f"sha256 {release['sha256']} (pending publication)."
    )


if __name__ == "__main__":
    main()
