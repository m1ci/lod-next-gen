#!/usr/bin/env python3
import yaml
import requests
from datetime import datetime, date
import hashlib
import os


# Path to your YAML file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_FILE = os.path.join(SCRIPT_DIR, "metadata.yaml")

# Base URL to check DBLP RDF releases
BASE_URL = "https://drops.dagstuhl.de/storage/artifacts/dblp/rdf"

# URL pattern for monthly snapshot files
FILE_PATTERN = "dblp-{year}-{month:02d}-01.nt.gz"

def get_current_yaml_version():
    """Reads the YAML and returns the latest version date and the YAML data."""
    if not os.path.exists(YAML_FILE):
        raise FileNotFoundError(f"{YAML_FILE} not found")

    with open(YAML_FILE, "r") as f:
        data = yaml.safe_load(f)

    latest_version_entry = data['artifacts'][0]['versions'][-1]
    latest_version_str = latest_version_entry['version']  # e.g., "2025-10-01"
    latest_version_date = latest_version_str  # already a date object

    return latest_version_date, data

def fetch_latest_release_date():
    """Checks the latest available release by querying the URL pattern."""
    today = date.today()
    # DBLP releases are monthly, usually on the 1st
    year, month = today.year, today.month
    # Try the current month first
    candidate_date = date(year, month, 1)
    url = f"{BASE_URL}/{year}/dblp-{year}-{month:02d}-01.nt.gz"

    response = requests.head(url)
    if response.status_code == 200:
        return candidate_date, url
    else:
        # fallback: check previous month
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        candidate_date = date(prev_year, prev_month, 1)
        url = f"{BASE_URL}/{prev_year}/dblp-{prev_year}-{prev_month:02d}-01.nt.gz"
        response = requests.head(url)
        if response.status_code == 200:
            return candidate_date, url
    return None, None

def calculate_sha256(url):
    """Downloads file in chunks to calculate sha256."""
    h = hashlib.sha256()
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            h.update(chunk)
    return h.hexdigest()

def update_yaml(new_date, url, data):
    """Adds a new version entry to the YAML."""
    new_version_str = new_date.strftime("%Y-%m-%d")  # "2025-10-01"
    new_version_entry = {
        "version": datetime.strptime(new_version_str, "%Y-%m-%d").date(),
        "title": f"DBLP RDF Release of {new_date.strftime('%B %Y')}",
        "description": "This file contains all the dblp RDF/N-Triple data in a single file. The dblp computer science bibliography is the open indexing service and knowledge graph of the computer science community. This version and its associated metadata have been **automatically retrieved and published** by an automated update process.",
        "license": data['license'],
        "distributions": [
            {
                "file": url,
                "format": "nt",
                "compression": "gz",
                "size": 4745938862,
                "sha256": "6b148c103921f48a2bfa290bd1c7d86730d1a551fce63425a4dc3aa3d63c390f",
                "status": "pending"
            }
        ]
    }

    # Optionally calculate sha256 (comment out if large file)
    # print("Calculating SHA256, this may take a while...")
    # new_version_entry['distributions'][0]['sha256'] = calculate_sha256(url)

    data['artifacts'][0]['versions'].append(new_version_entry)

    with open(YAML_FILE, "w") as f:
        yaml.dump(data, f, sort_keys=False)

    print(f"YAML updated with new version {new_version_str}")

def main():
    current_version_date, data = get_current_yaml_version()
    latest_release_date, url = fetch_latest_release_date()

    if latest_release_date is None:
        print("No new DBLP release found.")
        return

    if latest_release_date > current_version_date:
        print(f"New DBLP release found: {latest_release_date}")
        update_yaml(latest_release_date, url, data)
    else:
        print("YAML is already up to date.")

if __name__ == "__main__":
    main()
