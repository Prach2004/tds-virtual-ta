import requests
import json
import os
from tqdm import tqdm
from datetime import datetime

# Base settings
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
CATEGORY_ID = 34
DATA_DIR = "data/discourse"
OUTPUT_FILE = os.path.join(DATA_DIR, "discourse_posts.json")

# Date range
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 4, 14)

# Optional API Key (if needed)
API_KEY = ""         # e.g., "your_api_key"
API_USERNAME = ""    # e.g., "your_username"

# Add headers if using an API key
HEADERS = {
    "Api-Key": API_KEY,
    "Api-Username": API_USERNAME
} if API_KEY and API_USERNAME else {}

def fetch_category_topics():
    # Try the 'latest.json' endpoint for public access
    url = f"{BASE_URL}/c/courses/tds-kb/{CATEGORY_ID}/l/latest.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["topic_list"]["topics"]

def fetch_topic_detail(topic_id):
    url = f"{BASE_URL}/t/{topic_id}.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def within_date_range(date_str):
    post_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
    return START_DATE <= post_date <= END_DATE

def main():
    print("Fetching topic list...")
    try:
        topics = fetch_category_topics()
    except requests.HTTPError as e:
        print("❌ Failed to fetch topics:", e)
        return

    all_posts = []

    print(f"🔍 Filtering topics between {START_DATE.date()} and {END_DATE.date()}")
    for topic in tqdm(topics):
        topic_id = topic["id"]
        try:
            topic_data = fetch_topic_detail(topic_id)
        except requests.HTTPError as e:
            print(f"⚠️ Skipping topic {topic_id}: {e}")
            continue

        created_at = topic_data["created_at"]
        if not within_date_range(created_at):
            continue

        posts = topic_data["post_stream"]["posts"]
        all_posts.append({
            "id": topic_id,
            "title": topic_data["title"],
            "url": f"{BASE_URL}/t/{topic_id}",
            "created_at": created_at,
            "posts": [
                {
                    "username": post["username"],
                    "created_at": post["created_at"],
                    "cooked": post["cooked"]
                } for post in posts
            ]
        })

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2)

    print(f"✅ Saved {len(all_posts)} topics to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
