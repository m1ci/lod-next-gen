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


def get_latest_yaml_version(artifact):
    """
    Finds the newest published version of an artifact.
    """

    versions = artifact.get("versions", [])

    dates = []

    for entry in versions:
        try:
            dates.append(
                datetime.strptime(
                    str(entry["version"]),
                    "%Y-%m-%d"
                ).date()
            )
        except ValueError:
            pass

    if not dates:
        return None

    return max(dates)


def get_latest_version_metadata(artifact):
    """
    Returns the metadata of the latest existing version.
    Used as a template for the new version.
    """

    versions = artifact.get("versions", [])

    if not versions:
        return {}

    return max(
        versions,
        key=lambda x: datetime.strptime(
            str(x["version"]),
            "%Y-%m-%d"
        )
    )


def get_available_versions(prefix):
    """
    Finds all available DBnary releases for an artifact.
    """

    response = requests.get(BASE_URL)
    response.raise_for_status()

    html = response.text

    pattern = re.compile(
        re.escape(prefix) +
        r"(\d{8})\.ttl\.bz2"
    )

    releases = []

    for date_string in pattern.findall(html):

        version_date = datetime.strptime(
            date_string,
            "%Y%m%d"
        ).date()

        filename = (
            prefix +
            date_string +
            ".ttl.bz2"
        )

        url = BASE_URL + filename

        head = requests.head(url)

        size = int(
            head.headers.get(
                "Content-Length",
                0
            )
        )

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
    Gets the first missing version after current version.
    """

    candidates = [
        v for v in available_versions
        if current_version is None
        or v["version"] > current_version
    ]

    if not candidates:
        return None

    return candidates[0]


def create_version_entry(
    artifact,
    new_release
):
    """
    Creates a new version by copying metadata
    from the previous version.
    """

    previous = get_latest_version_metadata(
        artifact
    )

    entry = {}

    # Copy everything except version/distributions
    for key, value in previous.items():
        if key not in [
            "version",
            "distributions"
        ]:
            entry[key] = value

    entry["version"] = new_release["version"]

    # Ensure title is artifact name
    entry["title"] = artifact["artifact"]

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


def process_artifact(artifact):
    """
    Updates one DBnary artifact.
    """

    artifact_id = artifact.get("artifact")

    if not artifact_id:
        return

    prefix = artifact_id + "_"

    if prefix not in SUPPORTED_ARTIFACTS:
        return

    print("\nChecking:", artifact_id)

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

    new_version = get_next_version(
        current_version,
        available
    )

    if not new_version:
        print("No update available.")
        return

    print(
        "Adding version:",
        new_version["version"]
    )

    entry = create_version_entry(
        artifact,
        new_version
    )

    artifact["versions"].append(entry)


def main():

    data = load_yaml()

    for artifact in data.get(
        "artifacts",
        []
    ):
        process_artifact(
            artifact
        )

    save_yaml(data)

    print("\nDone.")


if __name__ == "__main__":
    main()