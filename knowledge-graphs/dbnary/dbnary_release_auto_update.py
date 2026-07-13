#!/usr/bin/env python3

import os
import re
import yaml
import requests
from datetime import datetime


# Path to metadata.yaml
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_FILE = os.path.join(SCRIPT_DIR, "metadata.yaml")

# DBnary release directory
BASE_URL = "https://kaiko.getalp.org/static/ontolex/en/"


# Supported DBnary artifacts
SUPPORTED_ARTIFACTS = [
    "en_dbnary_ontolex_",
    "en_dbnary_enhancement_",
    "en_dbnary_morphology_",
    "en_dbnary_lime_",
    "en_dbnary_statistics_",
    "en_dbnary_etymology_",
    "en_dbnary_exolex_ontolex_",
    "en_dbnary_exolex_lime_",
]


def get_artifact_prefix(data):
    """
    Detects which DBnary artifact is described by metadata.yaml.
    """

    artifact_id = data["artifacts"][0].get("artifact")

    if not artifact_id:
        raise ValueError(
            "Cannot determine artifact. "
            "Expected 'artifact' field in metadata.yaml"
        )

    artifact_prefix = artifact_id + "_"

    if artifact_prefix not in SUPPORTED_ARTIFACTS:
        raise ValueError(
            f"Unsupported DBnary artifact: {artifact_prefix}"
        )

    return artifact_prefix


def get_current_yaml_version(data):
    """
    Finds the newest version already published in metadata.yaml.
    Does not rely on ordering.
    """

    versions = data["artifacts"][0]["versions"]

    dates = []

    for version_entry in versions:
        version = str(version_entry["version"])

        try:
            version_date = datetime.strptime(
                version,
                "%Y-%m-%d"
            ).date()

            dates.append(version_date)

        except ValueError:
            print(
                f"Skipping unsupported version format: {version}"
            )

    if not dates:
        raise ValueError(
            "No valid versions found in metadata.yaml"
        )

    return max(dates)


def load_yaml():
    """
    Loads metadata.yaml.
    """

    if not os.path.exists(YAML_FILE):
        raise FileNotFoundError(
            f"{YAML_FILE} not found"
        )

    with open(YAML_FILE, "r") as f:
        return yaml.safe_load(f)


def get_available_versions(artifact_prefix):
    """
    Finds available DBnary releases for the selected artifact.

    Example:
    en_dbnary_lime_20260601.ttl.bz2
    """

    response = requests.get(BASE_URL)
    response.raise_for_status()

    html = response.text

    versions = []

    pattern = re.compile(
        re.escape(artifact_prefix) +
        r"(\d{8})\.ttl\.bz2"
    )

    for match in pattern.findall(html):

        version_date = datetime.strptime(
            match,
            "%Y%m%d"
        ).date()

        filename = (
            f"{artifact_prefix}"
            f"{match}.ttl.bz2"
        )

        url = BASE_URL + filename

        # Get exact file size
        head = requests.head(url)

        if head.status_code == 200:
            size = int(
                head.headers.get(
                    "Content-Length",
                    0
                )
            )
        else:
            size = 0

        versions.append(
            {
                "version": version_date,
                "url": url,
                "size": size,
            }
        )

    versions.sort(
        key=lambda x: x["version"]
    )

    return versions


def find_next_version(
    current_version,
    available_versions
):
    """
    Returns the first available version newer
    than the current YAML version.
    """

    newer_versions = [
        v for v in available_versions
        if v["version"] > current_version
    ]

    if not newer_versions:
        return None

    # Pick the next missing version, not the newest
    return min(
        newer_versions,
        key=lambda x: x["version"]
    )


def update_yaml(
    data,
    new_version
):
    """
    Adds the new DBnary version entry.
    """

    version_date = new_version["version"]

    entry = {
        "version": version_date,
        "title": "Monthly Snapshot",
        "abstract": (
            "DBnary provides multilingual lexical data "
            "extracted from Wiktionary and published as "
            "Linguistic Linked Open Data (LLOD)."
        ),
        "description": (
            "DBnary provides multilingual lexical data "
            "extracted from Wiktionary and published as "
            "Linguistic Linked Open Data (LLOD). "
            "This version and its metadata have been "
            "**automatically retrieved and published** "
            "by an automated update process.\n\n"
            "Found an issue? Update metadata in the "
            "DBpedia knowledge graph catalog."
        ),
        "license": data["license"],
        "distributions": [
            {
                "file": new_version["url"],
                "format": "ttl",
                "compression": "bz2",
                "size": new_version["size"],
                "sha256": None,
                "status": "pending",
            }
        ],
    }

    data["artifacts"][0]["versions"].append(entry)

    with open(YAML_FILE, "w") as f:
        yaml.dump(
            data,
            f,
            sort_keys=False
        )

    print(
        "Added new version:",
        version_date.strftime("%Y-%m-%d")
    )


def main():

    data = load_yaml()

    artifact_prefix = get_artifact_prefix(data)

    print(
        "Checking artifact:",
        artifact_prefix
    )

    current_version = get_current_yaml_version(data)

    print(
        "Current YAML version:",
        current_version
    )

    available_versions = get_available_versions(
        artifact_prefix
    )

    if not available_versions:
        print(
            "No DBnary releases found."
        )
        return

    next_version = find_next_version(
        current_version,
        available_versions
    )

    if not next_version:
        print(
            "No newer DBnary version available."
        )
        return

    print(
        "New DBnary version found:",
        next_version["version"]
    )

    update_yaml(
        data,
        next_version
    )


if __name__ == "__main__":
    main()