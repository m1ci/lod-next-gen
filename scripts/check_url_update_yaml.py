import yaml
import requests
import sys
from datetime import datetime

# Path to your YAML file
yaml_file = sys.argv[1]  # e.g., knowledge-graphs/dbpedia/metadata.yaml

# Load YAML
with open(yaml_file, "r") as f:
    data = yaml.safe_load(f)

updated = False
now = datetime.utcnow().isoformat() + "Z"

for dist in data.get("distributions", []):
    file_url = dist.get("file")
    if not file_url:
        continue
    try:
        resp = requests.head(file_url, allow_redirects=True, timeout=10)
        if resp.status_code == 200:
            dist["status"] = "active"
        else:
            dist["status"] = f"inactive ({resp.status_code})"
    except Exception as e:
        dist["status"] = f"inactive (error)"
    dist["last_verified"] = now
    updated = True

if updated:
    # Update the overall metadata timestamp
    data.setdefault("metadata", {})["last_checked"] = now

    # Write back YAML
    with open(yaml_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)

    print(f"Updated {yaml_file} with status and last_verified.")
else:
    print(f"No distributions found to update in {yaml_file}.")
