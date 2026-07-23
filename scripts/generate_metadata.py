import os
import re
from pathlib import Path

import yaml


body = os.environ.get("ISSUE_BODY", "")


def normalize_value(value):
    """
    Normalize GitHub Issue Form values.

    Converts:
    - "_No response_" -> None
    - empty strings -> None
    """

    if not value:
        return None

    value = value.strip()

    if value == "_No response_":
        return None

    if value == "":
        return None

    return value


def get_field(name):
    """
    Extract GitHub Issue Form field.
    """

    pattern = rf"### {re.escape(name)}\s*\n\s*(.*?)(?=\n### |\Z)"

    match = re.search(
        pattern,
        body,
        re.S
    )

    if match:
        return normalize_value(match.group(1))

    return None


def clean_yaml(text):
    """
    Remove Markdown YAML fences.

    Converts:

    ```yaml
    - artifact: example
    ```

    into pure YAML.
    """

    if not text:
        return text

    text = text.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        if lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines)

    return text.strip()


# --------------------------------------------------
# Extract fields
# --------------------------------------------------

kg_id = get_field(
    "KG ID"
)

title = get_field(
    "KG Title"
)

abstract = get_field(
    "KG Short Abstract"
)

description = get_field(
    "KG Full Description"
)

license_url = get_field(
    "License"
)

homepage = get_field(
    "KG Homepage"
)

domain = get_field(
    "KG Primary Domain"
)

keywords_text = get_field(
    "Keywords"
)

sparql_url = get_field(
    "SPARQL Endpoint URL"
)

maintainer_name = get_field(
    "KG Maintainer Name"
)

maintainer_contact = get_field(
    "KG Maintainer Contact"
)

maintainer_github = get_field(
    "KG Maintainer GitHub Username"
)

artifacts_text = get_field(
    "KG Content (Artifacts, Versions and Distributions)"
)


# --------------------------------------------------
# Validate required fields
# --------------------------------------------------

if not domain:

    raise ValueError(
        "KG Primary Domain is required"
    )


# --------------------------------------------------
# Parse keywords
# --------------------------------------------------

keywords = []

if keywords_text:

    keywords = [
        x.strip()
        for x in keywords_text.split(",")
        if x.strip()
    ]


# --------------------------------------------------
# Parse artifacts
# --------------------------------------------------

artifacts = []

if artifacts_text:

    artifacts = yaml.safe_load(
        clean_yaml(
            artifacts_text
        )
    )

    # Ensure every distribution has status: pending
    if artifacts:

        for artifact in artifacts:

            for version in artifact.get(
                "versions",
                []
            ):

                for distribution in version.get(
                    "distributions",
                    []
                ):

                    distribution["status"] = "pending"


# --------------------------------------------------
# Build metadata YAML
# --------------------------------------------------

metadata = {

    "databus-account":
        "knowledge-graph-catalog",

    "id":
        kg_id,

    "title":
        title,

    "abstract":
        abstract,

    "description":
        description,

    "moss-publish":
        True,

    "databus-publish":
        True,

    "license":
        license_url,

    "domains":
        [
            domain
        ],

    "keywords":
        keywords,

    "artifacts":
        artifacts
}


# --------------------------------------------------
# Optional homepage
# --------------------------------------------------

if homepage:

    metadata["homepage"] = homepage


# --------------------------------------------------
# Optional SPARQL endpoint
# --------------------------------------------------

if sparql_url:

    metadata["sparql"] = [
        {
            "name": "main",
            "url": sparql_url
        }
    ]


# --------------------------------------------------
# Optional maintainer
# --------------------------------------------------

if any([
    maintainer_name,
    maintainer_contact,
    maintainer_github
]):

    maintainer = {}

    if maintainer_name:

        maintainer["name"] = maintainer_name

    if maintainer_contact:

        maintainer["contact"] = maintainer_contact

    if maintainer_github:

        maintainer["github"] = maintainer_github

    metadata["maintainers"] = [
        maintainer
    ]


# --------------------------------------------------
# Create output directory
# --------------------------------------------------

output_dir = Path(
    "knowledge-graphs"
) / kg_id


output_dir.mkdir(
    parents=True,
    exist_ok=True
)


output_file = (
    output_dir /
    "metadata.yaml"
)


# --------------------------------------------------
# Write YAML
# --------------------------------------------------

with output_file.open(
    "w",
    encoding="utf-8"
) as f:

    yaml.dump(
        metadata,
        f,
        allow_unicode=True,
        sort_keys=False
    )


print(
    f"Generated {output_file}"
)
