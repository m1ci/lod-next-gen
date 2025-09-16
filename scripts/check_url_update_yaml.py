import yaml
import requests
import sys

yaml_file = sys.argv[1]

# --- Step 1: Validate YAML syntax ---
try:
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"❌ YAML format error in {yaml_file}: {e}")
    sys.exit(1)

if not data:
    print(f"No data loaded from {yaml_file}")
    sys.exit(0)

changed = False  # Track if any updates were made

# --- Step 2: Traverse artifacts -> versions -> distributions ---
for artifact in data.get("artifacts", []):
    for version in artifact.get("versions", []):
        for dist in version.get("distributions", []):
            url = dist.get("file")
            if not url:
                continue

            # Only check distributions with status: pending
            if dist.get("status") != "pending":
                continue

            try:
                resp = requests.head(url, allow_redirects=True, timeout=10)
                new_status = "active" if resp.status_code == 200 else "error"
            except requests.RequestException:
                new_status = "error"

            if dist.get("status") != new_status:
                print(f"🔄 Updating {url}: {dist.get('status')} -> {new_status}")
                dist["status"] = new_status
                changed = True
            else:
                print(f"✅ No change for {url} (still {dist.get('status')})")

# --- Step 3: Save only if something changed ---
if changed:
    with open(yaml_file, "w") as f:
        yaml.dump(data, f, sort_keys=False)
    print(f"💾 Updated {yaml_file}")
else:
    print(f"ℹ️ No changes needed for {yaml_file}")
