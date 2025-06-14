from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import faiss
import requests
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
EMBED_URL = f"{BASE_URL}/embeddings"
CHAT_URL = f"{BASE_URL}/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# FastAPI app setup
app = FastAPI()

# CORS for frontend dev (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class QuestionRequest(BaseModel):
    question: str
    attachments: Optional[List[str]] = None  # base64 strings, not used yet

# Load FAISS index and metadata
index = faiss.read_index("embeddings/vector.index")
with open("embeddings/metadata.json", "r", encoding="utf-8") as f:
    metadata = json.load(f)


# Function: Embed a single text input
def embed_text(text: str) -> List[float]:
    response = requests.post(EMBED_URL, headers=HEADERS, json={
        "model": EMBED_MODEL,
        "input": text
    })
    return response.json()["data"][0]["embedding"]

# Function: Search top_k similar chunks from index
def search_index(query_vector, top_k=5) -> List[dict]:
    D, I = index.search(np.array([query_vector]).astype("float32"), top_k)
    return [metadata[i] for i in I[0] if i < len(metadata)]

# Function: Call GPT with context and get answer
def generate_answer(question: str, context_chunks: List[dict]) -> str:
    context = "\n\n".join([chunk["text"] for chunk in context_chunks])

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful and precise teaching assistant. "
                "Always answer based on the given context. "
                "If applicable, include specific links or phrases from the materials. "
                "Do not make up information. Keep the answer short and focused."
            )
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nRelevant Materials:\n{context}"
        }
    ]

    response = requests.post(CHAT_URL, headers=HEADERS, json={
        "model": MODEL,
        "messages": messages
    })

    return response.json()["choices"][0]["message"]["content"]

# API endpoint
@app.post("/api/")
async def answer_question(req: QuestionRequest):
    try:
        question = req.question
        attachments = req.attachments or []

        embedding = embed_text(req.question)
        top_chunks = search_index(embedding, top_k=5)
        answer = generate_answer(req.question, top_chunks)
        links = [{"url": c["source"], "text": c["text"][:100]} for c in top_chunks if "source" in c]

        return {"answer": answer, "links": links}

    except Exception as e:
        return {"error": str(e)}
