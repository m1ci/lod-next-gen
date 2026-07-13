#!/usr/bin/env python3

import os
import re
import yaml
import requests
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_FILE = os.path.join(SCRIPT_DIR, "metadata.yaml")

BASE_URL = "https://kaiko.getalp.org/static/ontolex/en/"


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


def load_yaml():
    if not os.path.exists(YAML_FILE):
        raise FileNotFoundError(YAML_FILE)

    with open(YAML_FILE, "r") as f:
        return yaml.safe_load(f)


def save_yaml(data):
    with open(YAML_FILE, "w") as f:
        yaml.dump(
            data,
            f,
            sort_keys=False,
            allow_unicode=True
        )


def normalize_date(value):
    """
    Converts YAML dates or strings into datetime.date.
    """

    if hasattr(value, "year"):
        return value

    return datetime.strptime(
        str(value),
        "%Y-%m-%d"
    ).date()


def get_latest_yaml_version(artifact):
    """
    Finds the newest published version of an artifact.
    """

    versions = artifact.get("versions", [])

    dates = []

    for entry in versions:
        try:
            dates.append(
                normalize_date(
                    entry["version"]
                )
            )
        except Exception:
            print(
                "Skipping invalid YAML version:",
                entry.get("version")
            )

    if not dates:
        return None

    return max(dates)


def get_latest_version_metadata(artifact):
    """
    Returns the newest existing version entry.
    Used as metadata template.
    """

    versions = artifact.get(
        "versions",
        []
    )

    if not versions:
        return {}

    return max(
        versions,
        key=lambda x: normalize_date(
            x["version"]
        )
    )


def get_available_versions(prefix):
    """
    Finds all available DBnary releases for one artifact.
    """

    response = requests.get(
        BASE_URL
    )

    response.raise_for_status()

    html = response.text

    pattern = re.compile(
        re.escape(prefix) +
        r"(\d{8})\.ttl\.bz2"
    )

    releases = []

    for date_string in pattern.findall(html):

        # Ignore invalid historical dates
        try:
            version_date = datetime.strptime(
                date_string,
                "%Y%m%d"
            ).date()

        except ValueError:
            print(
                "Skipping invalid DBnary version:",
                date_string
            )
            continue


        filename = (
            prefix +
            date_string +
            ".ttl.bz2"
        )

        url = BASE_URL + filename


        try:
            head = requests.head(
                url,
                timeout=20
            )

            size = int(
                head.headers.get(
                    "Content-Length",
                    0
                )
            )

        except Exception:
            size = 0


        releases.append(
            {
                "version": version_date,
                "url": url,
                "size": size
            }
        )


    return sorted(
        releases,
        key=lambda x: x["version"]
    )


def get_next_version(
    current_version,
    available_versions
):
    """
    Returns the first available version after
    the current YAML version.
    """

    candidates = [
        version
        for version in available_versions
        if current_version is None
        or version["version"] > current_version
    ]

    if not candidates:
        return None

    return candidates[0]


def create_version_entry(
    artifact,
    new_release
):
    """
    Creates a new version entry.
    Copies metadata from previous version.
    """

    previous = get_latest_version_metadata(
        artifact
    )

    entry = {}

    # Copy existing metadata
    for key, value in previous.items():

        if key not in [
            "version",
            "title",
            "distributions"
        ]:
            entry[key] = value


    artifact_id = artifact.get(
        "artifact"
        or artifact.get("id")
        or artifact.get("name")
    )


    entry["version"] = new_release["version"]

    # Artifact name as title
    entry["title"] = artifact_id


    entry["distributions"] = [
        {
            "file": new_release["url"],
            "format": "ttl",
            "compression": "bz2",
            "size": new_release["size"],
            "sha256": None,
            "status": "pending"
        }
    ]


    return entry


def get_artifact_id(artifact):
    """
    Supports different YAML field names.
    """

    return (
        artifact.get("artifact")
        or artifact.get("id")
        or artifact.get("name")
    )


def process_artifact(artifact):

    artifact_id = get_artifact_id(
        artifact
    )

    if not artifact_id:
        return


    prefix = artifact_id

    if not prefix.endswith("_"):
        prefix += "_"


    if prefix not in SUPPORTED_ARTIFACTS:
        return


    print(
        "\nChecking:",
        artifact_id
    )


    current_version = get_latest_yaml_version(
        artifact
    )

    print(
        "Current version:",
        current_version
    )


    available = get_available_versions(
        prefix
    )


    print(
        "Available releases:",
        len(available)
    )


    new_version = get_next_version(
        current_version,
        available
    )


    if not new_version:
        print(
            "No update available."
        )
        return


    print(
        "Adding version:",
        new_version["version"]
    )


    entry = create_version_entry(
        artifact,
        new_version
    )


    artifact["versions"].append(
        entry
    )


def main():

    data = load_yaml()


    for artifact in data.get(
        "artifacts",
        []
    ):

        process_artifact(
            artifact
        )


    save_yaml(
        data
    )


    print(
        "\nDone."
    )


if __name__ == "__main__":
    main()