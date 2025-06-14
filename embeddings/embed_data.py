import os
import json
import faiss
import numpy as np
import requests
from tqdm import tqdm
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load token from .env
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")

# Endpoint
EMBED_URL = f"{BASE_URL}/embeddings"

# Files
DISCOURSE_FILE = "data/discourse/discourse_posts.json"
COURSE_DIR = "data/course_content"
FAISS_INDEX_FILE = "embeddings/vector.index"
METADATA_FILE = "embeddings/metadata.json"

MODEL = "text-embedding-3-small"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def get_embedding(text):
    payload = {
        "model": MODEL,
        "input": text
    }
    response = requests.post(EMBED_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()["data"][0]["embedding"]
    else:
        raise Exception(f"Embedding error {response.status_code}: {response.text}")

def clean_text(html):
    return BeautifulSoup(html, "html.parser").get_text()

def load_course_chunks():
    chunks = []
    for root, _, files in os.walk(COURSE_DIR):
        for fname in files:
            if fname.endswith((".md", ".py", ".txt", ".ipynb")):
                path = os.path.join(root, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    if len(text) > 100:
                        chunks.append((text, path))
                except Exception as e:
                    print(f"⚠️ Could not read {path}: {e}")
    return chunks

def load_discourse_chunks():
    chunks = []
    try:
        with open(DISCOURSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for topic in data:
            for post in topic["posts"]:
                text = clean_text(post["cooked"])
                if len(text) > 50:
                    chunks.append((text, topic["url"]))
    except Exception as e:
        print(f"⚠️ Could not read Discourse file: {e}")
    return chunks

def main():
    print("🔄 Generating embeddings via AI Pipe...")
    texts_and_sources = load_course_chunks() + load_discourse_chunks()

    vectors = []
    metadata = []

    for text, source in tqdm(texts_and_sources, desc="🔍 Embedding"):  # Limit to 100 for testing
        try:
            emb = get_embedding(text)
            vectors.append(emb)
            metadata.append({
                "source": source,
                "text": text[:200]
            })
        except Exception as e:
            print(f"⚠️ Embedding failed for {source}: {e}")

    if vectors:
        dim = len(vectors[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(vectors).astype("float32"))

        os.makedirs("embeddings", exist_ok=True)
        faiss.write_index(index, FAISS_INDEX_FILE)
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Saved {len(vectors)} embeddings to FAISS.")
    else:
        print("❌ No embeddings were created.")

if __name__ == "__main__":
    main()
