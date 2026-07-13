#!/usr/bin/env python3
"""
Description: Handy script for removing a specific artifact version from DBpedia Databus.
Author: Milan Dojchinovski
Email: dojcinovski.milan@gmail.com
Date: 2026-07-13
License: CC BY 4.0
"""

import sys
import requests

# Base configuration
DATABUS_BASE = "https://databus.dbpedia.org"


def delete_resource(uri, api_key):
    """Delete a Databus resource using the REST API."""

    headers = {
        "accept": "application/json",
        "X-API-KEY": api_key,
        "Content-Type": "application/ld+json",
    }

    print(f"\n🗑️ Deleting:")
    print(uri)

    response = requests.delete(uri, headers=headers)

    if response.status_code in (200, 204):
        print("✅ Deleted successfully")
    else:
        print(f"❌ Failed ({response.status_code})")
        print(response.text)


def main():

    if len(sys.argv) != 6:
        print(
            "Usage:\n"
            "python3 remove-version.py "
            "<databus-account> <group-id> <artifact-id> <version> <api-key>"
        )
        sys.exit(1)

    user = sys.argv[1]
    group = sys.argv[2]
    artifact = sys.argv[3]
    version = sys.argv[4]
    api_key = sys.argv[5]

    version_uri = (
        f"{DATABUS_BASE}/{user}/{group}/{artifact}/{version}"
    )

    print("==============================================")
    print("DBpedia Databus Version Deletion")
    print("==============================================")
    print(f"Account : {user}")
    print(f"Group   : {group}")
    print(f"Artifact: {artifact}")
    print(f"Version : {version}")
    print("----------------------------------------------")
    print(f"URI     : {version_uri}")
    print("==============================================")

    confirm = input(
        "\n⚠️  Type 'yes' to permanently delete this version: "
    )

    if confirm.strip().lower() != "yes":
        print("Aborted.")
        sys.exit(0)

    delete_resource(version_uri, api_key)

    print("\nDone.")


if __name__ == "__main__":
    main()