import os
import requests
from urllib.parse import urljoin

# Config
OWNER = "23f3004008"
REPO = "TDS-Project1-Data"
BRANCH = "main"
SAVE_DIR = "data/course_content"
FILE_TYPES = [".ipynb", ".md", ".pdf", ".py"]

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"
RAW_BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "TDS-Scraper"
}

def download_file(path):
    raw_url = urljoin(RAW_BASE, path)
    save_path = os.path.join(SAVE_DIR, path)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    response = requests.get(raw_url)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Downloaded: {path}")
    else:
        print(f"❌ Failed: {path} (status {response.status_code})")

def crawl_directory(path=""):
    url = f"{API_URL}/{path}" if path else API_URL
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    items = response.json()

    for item in items:
        item_path = item["path"]
        if item["type"] == "file" and any(item_path.endswith(ext) for ext in FILE_TYPES):
            download_file(item_path)
        elif item["type"] == "dir":
            crawl_directory(item_path)

def main():
    print(f"🚀 Scraping course content from {OWNER}/{REPO} ...")
    crawl_directory()
    print("✅ Course content scraping complete.")

if __name__ == "__main__":
    main()
