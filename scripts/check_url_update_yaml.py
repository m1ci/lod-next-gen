import yaml
import requests
import sys
from datetime import datetime
import os

yaml_file = sys.argv[1]

# Load YAML
with open(yaml_file, "r") as f:
    data = yaml.safe_load(f)

if not data:
    print(f"No data loaded from {yaml_file}")
    sys.exit(0)

# Determine if YAML was modified
# (in CI/GitHub, you may always treat it as "modified" if pushed)
file_modified = True  # or compare file mtime with metadata.last_checked

updated = False  # Track if YAML needs to be rewritten

for dist in data.get("distributions", []):
    # Check if this distribution should be validated
    if dist.get("status") != "pending" and not file_modified:
        continue  # skip active distributions if YAML wasn't modified

    url = dist.get("file")
    if not url:
        continue

    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        dist["status"] = "active" if resp.status_code == 200 else "error"
    except requests.RequestException:
        dist["status"] = "error"

    # Update verification timestamp
    dist["last_verified"] = datetime.utcnow().isoformat() + "Z"
    updated = True

# Update last_checked at the dataset level if any distribution was updated
if updated:
    data.setdefault("metadata", {})["last_checked"] = datetime.utcnow().isoformat() + "Z"
    with open(yaml_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)
    print(f"Updated {yaml_file}")
else:
    print(f"No updates needed for {yaml_file}")