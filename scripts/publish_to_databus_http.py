import yaml
import requests
import os
import sys
import json

# --- Config ---
API_PUBLISH = "https://databus.dbpedia.org/api/publish?fetch-file-properties=false"
API_KEY = os.environ.get("DATABUS_API_KEY")
if not API_KEY:
    print("Error: DATABUS_API_KEY not set")
    sys.exit(1)

# YAML file path from argument
yaml_file = sys.argv[1]

# --- Load YAML ---
try:
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"❌ YAML format error: {e}")
    sys.exit(1)

if not data:
    print(f"No data loaded from {yaml_file}")
    sys.exit(1)

# --- Check databus-publish flag ---
if not data.get("databus-publish", False):
    print(f"Skipping {yaml_file}: databus-publish is false")
    sys.exit(0)

# --- Helper function ---
def send_publish(payload):
    print("=== Payload to publish ===")
    print(json.dumps(payload, indent=2))
    print("=========================")
    headers = {
        "accept": "application/json",
        "Content-Type": "application/ld+json",
        "X-API-KEY": API_KEY
    }
    resp = requests.post(API_PUBLISH, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()

# --- Step 1: Publish Group ---
group_id = f"https://databus.dbpedia.org/knowledge-graph-catalog/{data['id']}"
group_payload = {
    "@context": "https://databus.dbpedia.org/res/context.jsonld",
    "@graph": {
        "@id": group_id,
        "@type": "Group",
        "title": data["title"],
        "description": data.get("description", "")
    }
}
send_publish(group_payload)
print(f"✅ Published group: {group_id}")

# --- Step 2: Publish Artifacts & Versions ---
for artifact in data.get("artifacts", []):
    artifact_id = f"{group_id}/{artifact['artifact'].replace(' ', '-')}"
    artifact_payload = {
        "@context": "https://databus.dbpedia.org/res/context.jsonld",
        "@graph": {
            "@id": artifact_id,
            "@type": "Artifact",
            "title": artifact["title"],
            "description": artifact.get("description", "")
        }
    }
    send_publish(artifact_payload)
    print(f"✅ Published artifact: {artifact_id}")

    for version in artifact.get("versions", []):
        version_str = str(version['version'])
        version_id = f"{artifact_id}/{version_str.replace(' ', '-')}"
        dist_list = []
        for i, dist in enumerate(version.get("distributions", []), start=1):
            part_id = f"{version_id}#e{i}"
            dist_list.append({
                "@id": part_id,
                "@type": "Part",
                "formatExtension": dist.get("format"),
                "compression": dist.get("compression"),
                "sha256sum": dist.get("sha256"),
                "dcat:byteSize": dist.get("size"),
                "downloadURL": dist.get("file")
            })

        version_payload = {
            "@context": "https://databus.dbpedia.org/res/context.jsonld",
            "@graph": {
                "@type": "Version",
                "@id": version_id,
                "title": version["title"],
                "description": version.get("description", ""),
                "license": version.get("license", "https://creativecommons.org/licenses/by/4.0/"),
                "distribution": dist_list
            }
        }
        send_publish(version_payload)
        print(f"✅ Published version: {version_id}")

# --- Reset databus-publish flag ---
data["databus-publish"] = False
with open(yaml_file, "w") as f:
    yaml.dump(data, f, sort_keys=False)

print(f"💾 Reset databus-publish to false for {yaml_file}")
