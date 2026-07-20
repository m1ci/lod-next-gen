import os
import re
import requests


body = os.environ["ISSUE_BODY"]

errors = []


def get_field(name):
    """
    Extract GitHub issue form field.
    Example:

    ### KG ID

    my-kg
    """
    pattern = rf"### {re.escape(name)}\s+(.*?)(?=\n### |\Z)"
    match = re.search(pattern, body, re.S)

    if match:
        return match.group(1).strip()

    return None


# ----------------------
# Validate KG ID
# ----------------------

kg_id = get_field("KG ID")

if not kg_id:
    errors.append("KG ID is missing")

elif not re.match(r"^[a-z0-9-]+$", kg_id):
    errors.append(
        "KG ID must contain only lowercase letters, numbers and hyphens"
    )


# ----------------------
# Validate title
# ----------------------

title = get_field("KG Title")

if not title:
    errors.append("KG Title is missing")


# ----------------------
# Validate homepage
# ----------------------

homepage = get_field("Homepage")

if homepage:
    if not homepage.startswith(("http://", "https://")):
        errors.append(
            f"Homepage is not a valid URL: {homepage}"
        )


# ----------------------
# Result
# ----------------------

if errors:

    message = """
## ❌ KG validation failed

The following problems were found:

"""

    for e in errors:
        message += f"- {e}\n"

else:

    message = """
## ✅ KG validation successful

The KG metadata passed the initial validation checks.
"""


print(message)
