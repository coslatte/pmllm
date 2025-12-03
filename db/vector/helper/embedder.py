import os
import time
from typing import List, Sequence

import requests

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat")
EMBEDDING_API_URL = (
    os.getenv("EMBEDDING_API_URL")
    or os.getenv("EMBEDDING_URL")
    or "http://localhost:9000/v1/embeddings"
)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or os.getenv("MODEL_API_KEY")
EMBEDDING_TIMEOUT = float(os.getenv("EMBEDDING_API_TIMEOUT", "60"))
MAX_RETRIES = 5
RETRY_DELAY = 2.0


def _build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if EMBEDDING_API_KEY:
        headers["Authorization"] = f"Bearer {EMBEDDING_API_KEY}"
    return headers


def _call_embedding_endpoint(payload: dict) -> List[List[float]]:
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                EMBEDDING_API_URL,
                json=payload,
                headers=_build_headers(),
                timeout=EMBEDDING_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            embeddings_data = data.get("data")
            if not embeddings_data:
                raise RuntimeError("Embedding API response does not contain 'data'.")

            # Ensure deterministic ordering by index when provided
            if isinstance(embeddings_data[0], dict) and "index" in embeddings_data[0]:
                embeddings_data = sorted(embeddings_data, key=lambda item: item.get("index", 0))

            vectors: List[List[float]] = []
            for item in embeddings_data:
                vector = item.get("embedding")
                if not isinstance(vector, Sequence):
                    raise RuntimeError("Embedding item missing 'embedding' field")
                vectors.append(list(vector))
            return vectors

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < MAX_RETRIES - 1:
                sleep_time = RETRY_DELAY * (2**attempt)
                print(f"Embedding API connection error: {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                raise
        except Exception as e:
            # For other errors (e.g. 400 Bad Request), fail immediately or retry?
            # 500 errors should probably be retried too.
            if isinstance(e, requests.exceptions.HTTPError) and 500 <= e.response.status_code < 600:
                if attempt < MAX_RETRIES - 1:
                    sleep_time = RETRY_DELAY * (2**attempt)
                    print(f"Embedding API server error: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
            raise

    raise RuntimeError("Max retries exceeded for embedding API")


def embed(text: str) -> List[float]:
    """Return a single embedding vector produced by the model gateway."""

    vectors = _call_embedding_endpoint({"model": EMBEDDING_MODEL, "input": text})
    if not vectors:
        raise RuntimeError("Embedding API returned an empty result set")
    return vectors[0]


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a batch of texts.

    Args:
        texts: List of strings to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    try:
        return _call_embedding_endpoint({"model": EMBEDDING_MODEL, "input": texts})
    except Exception as exc:
        print(f"Embedding batch request failed ({exc}); retrying sequentially.")
        # Try sequential with the same retry logic in embed()
        results = []
        for t in texts:
            try:
                results.append(embed(t))
            except Exception as e:
                print(f"Failed to embed single item: {e}")
                raise
        return results
