import requests
from bs4 import BeautifulSoup
import yaml
import re
from datetime import datetime
from urllib.parse import urljoin

# --- Load existing metadata ---
with open("metadata.yaml", "r") as f:
    metadata = yaml.safe_load(f)

# --- Fetch the DNB Open Data page ---
base_url = "https://data.dnb.de/opendata/"
resp = requests.get(base_url)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

# --- Fetch the checksum file ---
checksum_url = urljoin(base_url, "001_Pruefsumme_Checksum.txt")
resp_checksum = requests.get(checksum_url)
resp_checksum.raise_for_status()

checksum_lines = resp_checksum.text.strip().splitlines()
checksum_dict = {}
for line in checksum_lines:
    parts = line.strip().split()
    if len(parts) == 2:
        sha256, fname = parts
        checksum_dict[fname] = sha256

# --- Collect all .gz links with a date in filename ---
links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if href.endswith(".gz"):
        filename = href.split("/")[-1]
        if re.search(r"_\d{8}", filename):
            full_url = urljoin(base_url, href)
            links.append((full_url, a))  # store both URL and anchor tag

# --- Helper: get description for non-versioned file ---
def get_description_for_base(base_name):
    for a in soup.find_all("a", href=True):
        href = a["href"]
        filename = href.split("/")[-1]
        # Match non-versioned file
        if re.match(rf"{re.escape(base_name)}\.(ttl|rdf|jsonld|hdt)\.gz", filename):
            description = ""
            for sib in a.next_siblings:
                if isinstance(sib, str):
                    description += sib.strip()
                else:
                    break
            description = re.sub(r'\s+', ' ', description)
            description = re.split(r'\sFormat', description)[0].strip()[:-1]
            description += ". This version has been **auto-generated**."
            return description
    return "Description missing."

# --- Group files into artifacts by base name (without date and extension) ---
artifacts_dict = {}
for link, a_tag in links:
    filename = link.split("/")[-1]
    match = re.match(r"(authorities-gnd.+?)_(\d{8})\.(ttl|rdf|jsonld|hdt)\.gz", filename)
    if match:
        base_name, version_date_str, ext = match.groups()
        artifact_key = base_name
        if artifact_key not in artifacts_dict:
            description = get_description_for_base(base_name)  # <- updated here
            artifacts_dict[artifact_key] = {
                "artifact": base_name,
                "title": base_name,
                "description": description,
                "versions": []
            }

        version_date = datetime.strptime(version_date_str, "%Y%m%d").date()
        version_entry = next(
            (v for v in artifacts_dict[artifact_key]["versions"] if v["version"] == version_date),
            None
        )
        if not version_entry:
            version_entry = {
                "version": version_date,
                "title": base_name,
                "description": artifacts_dict[artifact_key]["description"],
                "license": metadata.get("license"),
                "distributions": []
            }
            artifacts_dict[artifact_key]["versions"].append(version_entry)

        sha256_value = checksum_dict.get(filename, "missing")

        # --- Fetch file size using HEAD request ---
        try:
            head_resp = requests.head(link, allow_redirects=True)
            size_bytes = int(head_resp.headers.get("Content-Length", 0))
        except Exception:
            size_bytes = 0

        version_entry["distributions"].append({
            "file": link,  # full download URL
            "format": ext,
            "compression": "gz",
            "size": size_bytes,
            "sha256": sha256_value,
            "status": "pending"
        })

# --- Convert artifacts dict to list ---
metadata["artifacts"] = list(artifacts_dict.values())

# --- Save updated metadata ---
with open("metadata_with_artifacts.yaml", "w") as f:
    yaml.dump(metadata, f, sort_keys=False, default_flow_style=False)

print("✅ Metadata updated and saved to metadata_with_artifacts.yaml")
