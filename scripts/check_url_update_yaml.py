import yaml
import requests
import sys
from datetime import datetime

yaml_file = sys.argv[1]

# Load YAML
with open(yaml_file, "r") as f:
    data = yaml.safe_load(f)

if not data:
    print(f"No data loaded from {yaml_file}")
    sys.exit(0)

updated = False  # Flag to track if we need to write YAML back

for dist in data.get("distributions", []):
    # Skip distributions whose status is not "pending"
    if dist.get("status") != "pending":
        continue

    url = dist.get("file")
    if not url:
        continue

    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        if resp.status_code == 200:
            dist["status"] = "active"
        else:
            dist["status"] = "error"
    except requests.RequestException:
        dist["status"] = "error"

    # Update verification timestamp
    dist["last_verified"] = datetime.utcnow().isoformat() + "Z"
    updated = True

# Only write YAML if something was updated
if updated:
    data.setdefault("metadata", {})["last_checked"] = datetime.utcnow().isoformat() + "Z"
    with open(yaml_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)
    print(f"Updated {yaml_file}")
else:
    print(f"No updates needed for {yaml_file}")
