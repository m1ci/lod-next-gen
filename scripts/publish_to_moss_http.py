import os
import sys
import yaml
import requests

API_URL = "https://moss.dev.dbpedia.link/api/v1/save-entry"

yaml_file = sys.argv[1]

# -----------------------
# Load YAML
# -----------------------

try:
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"❌ YAML format error: {e}")
    sys.exit(1)

if not data:
    print(f"No data loaded from {yaml_file}")
    sys.exit(1)

# -----------------------
# Publish flag
# -----------------------

if not data.get("moss-publish", False):
    print(f"Skipping {yaml_file}: moss-publish is false")
    sys.exit(0)

# -----------------------
# API Key
# -----------------------

API_KEY = os.environ.get("MOSS_KG_CATALOG")

if not API_KEY:
    print("❌ Environment variable MOSS_KG_CATALOG is not set")
    sys.exit(1)

# -----------------------
# Required metadata
# -----------------------

databus_account = data.get("databus-account")
dataset_id = data.get("id")

if not databus_account:
    raise ValueError("Missing databus-account")

if not dataset_id:
    raise ValueError("Missing id")

resource = f"https://databus.dbpedia.org/{databus_account}/{dataset_id}"

keywords = data.get("keywords", [])

if not keywords:
    print(f"⚠️ No keywords defined for {yaml_file}. Nothing to publish.")
    data["moss-publish"] = False

    with open(yaml_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)

    sys.exit(0)

# -----------------------
# Build Turtle
# -----------------------

ttl = """PREFIX schema: <https://schema.org/>

<%s>
""" % resource

for kw in keywords:
    escaped = str(kw).replace('"', '\\"')
    ttl += f'    schema:keywords "{escaped}" ;\n'

ttl = ttl.rstrip(" ;\n") + " .\n"

print("=== Turtle ===")
print(ttl)
print("================")

# -----------------------
# POST
# -----------------------

headers = {
    "accept": "application/json",
    "X-API-KEY": API_KEY,
    "Content-Type": "text/turtle",
}

params = {
    "module": "keyword",
    "resource": resource,
}

response = requests.post(
    API_URL,
    params=params,
    headers=headers,
    data=ttl.encode("utf-8"),
)

try:
    response.raise_for_status()
except requests.HTTPError:
    print(response.text)
    raise

print(f"✅ Published keywords for {resource}")

# -----------------------
# Reset publish flag
# -----------------------

data["moss-publish"] = False

with open(yaml_file, "w") as f:
    yaml.dump(data, f, sort_keys=False)

print(f"💾 Updated {yaml_file} and reset moss-publish to false")