import yaml
import requests
import os
import sys
from datetime import datetime
import json

# --- Config ---
API_URL = "https://databus.dbpedia.org/api/publish?fetch-file-properties=false"
API_KEY = os.environ.get("DATABUS_API_KEY")
if not API_KEY:
    print("Error: DATABUS_API_KEY not set")
    sys.exit(1)

# YAML file path from argument
yaml_file = sys.argv[1]

# Load YAML
with open(yaml_file, "r") as f:
    data = yaml.safe_load(f)

if not data:
    print(f"No data loaded from {yaml_file}")
    sys.exit(1)

# Prepare JSON-LD payload
version_id = f"https://databus.dbpedia.org/m1ci/{data['databus']['group']}/{data['databus']['artifact']}/{data['databus']['latest_version']}"

payload = {
    "@context": "https://databus.dbpedia.org/res/context.jsonld",
    "@graph": {
        "@type": "Version",
        "@id": version_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "license": data["license"],
        "distribution": []
    }
}

for dist in data.get("distributions", []):
    part_id = version_id + "#e"
    payload["@graph"]["distribution"].append({
        "@id": part_id,
        "@type": "Part",
        "formatExtension": dist.get("format"),
        "compression": dist.get("compression"),
        "sha256sum": dist.get("sha256"),
        "dcat:byteSize": dist.get("size"),
        "downloadURL": dist.get("file")
    })

# Prepare headers
headers = {
    "accept": "application/json",
    "Content-Type": "application/ld+json",
    "X-API-KEY": API_KEY
}

# --- Debug: print request before sending ---
print("=== Databus Publish Request ===")
print("URL:", API_URL)
print("Headers:", json.dumps(headers, indent=2))
print("Payload:", json.dumps(payload, indent=2))
print("=== End of Request ===")

# Confirm before sending
confirm = input("Send request to Databus? [y/N]: ").strip().lower()
if confirm != "y":
    print("Aborted by user")
    sys.exit(0)

# Send POST request to Databus
resp = requests.post(API_URL, headers=headers, json=payload)
resp.raise_for_status()
result = resp.json()

# Update YAML with Databus URL (stable URL returned by API)
data["databus"]["url"] = version_id
data["databus"]["latest_version"] = data["databus"]["latest_version"]
now = datetime.utcnow().isoformat() + "Z"
for dist in data.get("distributions", []):
    dist["status"] = "active"
    dist["last_verified"] = now
data.setdefault("metadata", {})["last_checked"] = now

# Write back YAML
with open(yaml_file, "w") as f:
    yaml.dump(data, f, sort_keys=False)

print(f"Published {yaml_file} to Databus, updated YAML with URL and verification info.")
