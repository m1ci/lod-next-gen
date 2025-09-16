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

for dist in data.get("distributions", []):

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

    with open(yaml_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)
    print(f"Checked {yaml_file}")
