#!/usr/bin/env python3
import yaml
import requests
import sys
import subprocess
import os


# Path to your YAML file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
metadata_file = os.path.join(SCRIPT_DIR, "metadata.yaml")


def main():
    metadata_file = "metadata.yaml"

    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: {metadata_file} not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing {metadata_file}: {e}")
        sys.exit(1)

    # Extract required metadata fields
    databus_account = data.get("databus-account")
    group_id = data.get("id")
#    api_key = "bla bla"
    api_key = os.environ.get(databus_account)
    
    if not databus_account or not group_id:
        print("❌ Missing required fields (databus-account or id) in metadata.yaml")
        sys.exit(1)

    if not api_key:
        print("⚠️ Warning: API key not provided via environment variable 'DATABUS_API_KEY'.")
        print("   Please set it using: export DATABUS_API_KEY=your_api_key")
        sys.exit(1)

    try:
        artifacts = data.get("artifacts", [])
        if not artifacts:
            raise ValueError("No artifacts found in metadata.yaml")

        first_artifact = artifacts[0]
        versions = first_artifact.get("versions", [])
        if not versions:
            raise ValueError("No versions found in artifact")

        first_version = versions[0]
        distributions = first_version.get("distributions", [])
        if not distributions:
            raise ValueError("No distributions found in version")

        file_url = distributions[0].get("file")
        if not file_url:
            raise ValueError("No file URL found in distribution")

    except (KeyError, IndexError, ValueError) as e:
        print(f"❌ Error extracting file URL: {e}")
        sys.exit(1)

    # Show which URL will be checked
    print(f"🔍 Checking file URL: {file_url}")

    # Check if the file is reachable
    try:
        response = requests.head(file_url, allow_redirects=True, timeout=10)
        if response.status_code == 200:
            print("✅ The current GND release is valid.")
            return
        else:
            print(f"⚠️ The current GND release is no longer available. (status: {response.status_code})")
    except requests.RequestException as e:
        print(f"⚠️ The current GND release is no longer available. (Error accessing file: {e})")

    # Run remove-group.py if file unavailable
    print("🧹 Running remove-group.py to remove group...")
#    try:
#        result = subprocess.run(
#            ["python3", "remove-group.py", databus_account, group_id, api_key],
#            capture_output=True,
#            text=True,
#            check=True
#        )
#        print("✅ remove-group.py executed successfully.")
#        print(result.stdout)
#    except subprocess.CalledProcessError as e:
#        print("❌ Error running remove-group.py:")
#        print(e.stderr)
#        sys.exit(1)

if __name__ == "__main__":
    main()
