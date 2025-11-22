import os
from typing import Any, List
import sys
import requests

# Use LM Studio API for embeddings to avoid local torch issues
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://localhost:1234/v1/embeddings")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-qwen3-embedding-0.6b")

def embed(text: str) -> List[float]:
    """Return the embedding generated via LM Studio API.
    
    Args:
        text: The text to embed
        
    Returns:
        A list of floats representing the embedding vector
        
    Raises:
        RuntimeError: If the API call fails
    """
    try:
        response = requests.post(
            EMBEDDING_URL,
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        vector = data["data"][0]["embedding"]
        return list(vector)
    except Exception as e:
        raise RuntimeError(f"Failed to get embedding from API: {e}")
