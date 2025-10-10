#!/usr/bin/env python3
"""
Description: Handy script for removing a group and all artifacts/versions associated with it.
Author: Milan Dojchinovski
Email: dojcinovski.milan@gmail.com
Date: 2025-06-09
License: CC BY 4.0
"""

import sys
import requests
from SPARQLWrapper import SPARQLWrapper, JSON

# Base configuration
DATABUS_BASE = "https://databus.dbpedia.org"
SPARQL_ENDPOINT = "https://databus.dbpedia.org/sparql"


def query_sparql(query):
    """Run a SPARQL query and return results as bindings."""
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results["results"]["bindings"]


def get_artifacts(user, group):
    """Return a list of artifact URIs for the given user/group."""
    query = f"""
    PREFIX databus: <https://dataid.dbpedia.org/databus#>
    SELECT DISTINCT ?artifact WHERE {{
      ?artifact databus:group <https://databus.dbpedia.org/{user}/{group}> .
      ?artifact a databus:Artifact .
    }}
    """
    results = query_sparql(query)
    return [r["artifact"]["value"] for r in results]


def get_versions(user, group):
    """Return a list of version URIs for the given user/group."""
    query = f"""
    PREFIX databus: <https://dataid.dbpedia.org/databus#>
    SELECT DISTINCT ?version WHERE {{
      ?version databus:group <https://databus.dbpedia.org/{user}/{group}> .
      ?version a databus:Version .
    }}
    """
    results = query_sparql(query)
    return [r["version"]["value"] for r in results]


def delete_resource(uri, api_key):
    """Delete a Databus resource using the REST API."""
    headers = {
        "accept": "application/json",
        "X-API-KEY": api_key,
        "Content-Type": "application/ld+json",
    }

    print(f"🗑️  Deleting: {uri}")
    response = requests.delete(uri, headers=headers)

    if response.status_code in (200, 204):
        print("✅ Deleted successfully")
    else:
        print(f"❌ Failed to delete {uri} — {response.status_code}: {response.text}")


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 remove-group.py <databus-account> <group-id> <api-key>")
        sys.exit(1)

    user = sys.argv[1]
    group = sys.argv[2]
    api_key = sys.argv[3]

    print(f"🚀 Removing Databus group '{group}' for account '{user}'...")

    # Fetch and delete all versions
    print(f"\n📦 Fetching all versions in group '{group}'...")
    versions = get_versions(user, group)
    for version_uri in versions:
        delete_resource(version_uri, api_key)

    # Fetch and delete all artifacts
    print(f"\n📚 Fetching all artifacts in group '{group}'...")
    artifacts = get_artifacts(user, group)
    for artifact_uri in artifacts:
        delete_resource(artifact_uri, api_key)

    # Finally, delete the group
    print(f"\n🧹 Deleting group '{group}' itself...")
    group_uri = f"{DATABUS_BASE}/{user}/{group}"
    delete_resource(group_uri, api_key)

    print("\n✅ All deletions completed successfully.")


if __name__ == "__main__":
    main()
