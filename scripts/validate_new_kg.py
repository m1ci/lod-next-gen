import os
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml


body = os.environ.get("ISSUE_BODY", "")

errors = []
warnings = []


def get_field(name):
    """
    Extract GitHub Issue Form field.

    Example:
    
    ### KG ID

    my-kg

    ### KG Title

    My KG
    """

    pattern = rf"### {re.escape(name)}\s*\n\s*(.*?)(?=\n### |\Z)"

    match = re.search(pattern, body, re.S)

    if match:
        return match.group(1).strip()

    return None


def valid_url(value):
    if not value:
        return False

    try:
        result = urlparse(value)
        return result.scheme in ("http", "https") and result.netloc
    except Exception:
        return False


def add_error(message):
    errors.append(message)


def add_warning(message):
    warnings.append(message)


# --------------------------------------------------
# Extract fields
# --------------------------------------------------

kg_id = get_field("KG ID")
title = get_field("KG Title")
abstract = get_field("Abstract")
description = get_field("Description")
license_url = get_field("License")
homepage = get_field("Homepage")
domain = get_field("Primary Domain")
keywords = get_field("Keywords")

sparql_url = get_field("SPARQL Endpoint URL")

maintainer_name = get_field("Maintainer Name")
maintainer_contact = get_field("Maintainer Contact")

artifacts_text = get_field(
    "Artifacts, Versions and Distributions"
)


# --------------------------------------------------
# KG ID
# --------------------------------------------------

if not kg_id:
    add_error("KG ID is missing.")

elif not re.match(r"^[a-z0-9-]+$", kg_id):
    add_error(
        "KG ID must contain only lowercase letters, numbers and hyphens."
    )


# --------------------------------------------------
# Title
# --------------------------------------------------

if not title:
    add_error("KG Title is missing.")


# --------------------------------------------------
# Abstract
# --------------------------------------------------

if not abstract:
    add_error("Abstract is missing.")

elif len(abstract) > 300:
    add_error(
        "Abstract exceeds the maximum length of 300 characters."
    )


# --------------------------------------------------
# Description
# --------------------------------------------------

if not description:
    add_error("Description is missing.")


# --------------------------------------------------
# License
# --------------------------------------------------

if not license_url:
    add_error("License is missing.")

elif not valid_url(license_url):
    add_error(
        f"License is not a valid URL: {license_url}"
    )


# --------------------------------------------------
# Homepage
# --------------------------------------------------

if homepage and not valid_url(homepage):
    add_error(
        f"Homepage is not a valid URL: {homepage}"
    )


# --------------------------------------------------
# Domain
# --------------------------------------------------

allowed_domains = [
    "Cross-domain",
    "Geography & Environment",
    "Government & Public Sector",
    "Life Sciences & Health",
    "Economy, Industry & Infrastructure",
    "Publications, Education & Research",
    "Media, Culture & Entertainment",
    "Linguistics, Social & Digital Knowledge Systems",
]

if domain not in allowed_domains:
    add_error(
        f"Invalid domain: {domain}"
    )


# --------------------------------------------------
# Keywords
# --------------------------------------------------

if not keywords:
    add_error("Keywords are missing.")

else:
    keyword_list = [
        x.strip()
        for x in keywords.split(",")
        if x.strip()
    ]

    if len(keyword_list) < 3:
        add_error(
            "At least 3 keywords are required."
        )

    if len(keyword_list) > 8:
        add_error(
            "Maximum 8 keywords are allowed."
        )


# --------------------------------------------------
# SPARQL endpoint
# --------------------------------------------------

if sparql_url and not valid_url(sparql_url):
    add_error(
        f"SPARQL endpoint URL is invalid: {sparql_url}"
    )


# --------------------------------------------------
# Maintainer
# --------------------------------------------------

if not maintainer_name:
    add_error(
        "Maintainer name is missing."
    )

if not maintainer_contact:
    add_error(
        "Maintainer contact is missing."
    )

elif "@" not in maintainer_contact:
    add_error(
        "Maintainer contact does not look like an email address."
    )


# --------------------------------------------------
# Artifacts YAML
# --------------------------------------------------

if not artifacts_text:

    add_error(
        "Artifacts section is missing."
    )

else:

    try:

        artifacts = yaml.safe_load(artifacts_text)

        if not isinstance(artifacts, list):
            add_error(
                "Artifacts must be a YAML list."
            )

        else:

            for i, artifact in enumerate(artifacts):

                prefix = f"Artifact #{i+1}"

                if "artifact" not in artifact:
                    add_error(
                        f"{prefix}: missing artifact id."
                    )

                if "title" not in artifact:
                    add_error(
                        f"{prefix}: missing title."
                    )

                versions = artifact.get("versions")

                if not versions:
                    add_error(
                        f"{prefix}: no versions defined."
                    )

                else:

                    for j, version in enumerate(versions):

                        vprefix = (
                            f"{prefix}, version #{j+1}"
                        )

                        if "version" not in version:
                            add_error(
                                f"{vprefix}: missing version number."
                            )

                        if "license" not in version:
                            add_error(
                                f"{vprefix}: missing license."
                            )

                        distributions = (
                            version.get(
                                "distributions"
                            )
                        )

                        if not distributions:
                            add_error(
                                f"{vprefix}: no distributions defined."
                            )

                        else:

                            for k, dist in enumerate(distributions):

                                dprefix = (
                                    f"{vprefix}, distribution #{k+1}"
                                )

                                if "file" not in dist:
                                    add_error(
                                        f"{dprefix}: missing file URL."
                                    )

                                elif not valid_url(
                                    dist["file"]
                                ):
                                    add_error(
                                        f"{dprefix}: invalid file URL."
                                    )

                                if "format" not in dist:
                                    add_error(
                                        f"{dprefix}: missing format."
                                    )


    except yaml.YAMLError as e:

        add_error(
            f"Artifacts YAML is invalid: {e}"
        )


# --------------------------------------------------
# Generate GitHub comment
# --------------------------------------------------

if errors:

    result = """
## ❌ KG Metadata Validation Failed

The submission contains the following problems:

"""

    for error in errors:
        result += f"- {error}\n"


else:

    result = """
## ✅ KG Metadata Validation Passed

All mandatory metadata fields are valid.

"""

    if warnings:
        result += "\nWarnings:\n\n"

        for warning in warnings:
            result += f"- {warning}\n"


Path(
    "validation-result.md"
).write_text(
    result,
    encoding="utf-8"
)

print(result)
