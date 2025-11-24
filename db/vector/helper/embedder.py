import os
from typing import Any, List
import sys
import requests

# Configuration
USE_LOCAL_EMBEDDING = os.getenv("USE_LOCAL_EMBEDDING", "true").lower() == "true"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat")
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://localhost:1234/v1/embeddings")

_model = None


def _get_local_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            # 1. Try configured model OFFLINE
            try:
                print(f"Loading {EMBEDDING_MODEL} (offline)...")
                _model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
                return _model
            except Exception as e:
                print(f"Failed to load {EMBEDDING_MODEL} (offline): {e}")

            # 2. Try configured model ONLINE
            try:
                if input(
                    "Do you want to load the model online? [Y/n]"
                ).lower().strip() in ("yes", "y"):
                    print(f"Loading {EMBEDDING_MODEL} (online)...")
                    _model = SentenceTransformer(EMBEDDING_MODEL)
                    return _model
                else:
                    print("Exiting...")
                    sys.exit(0)
            except Exception as e:
                print(f"Failed to load {EMBEDDING_MODEL}: {e}")

            # 3. Fallback
            print("Falling back to 'all-mpnet-base-v2'...")
            try:
                _model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
                return _model
            except Exception as e:
                print(f"Failed to load fallback model: {e}")
                _model = None

        except ImportError:
            print("sentence_transformers not installed.")
            _model = None
    return _model


def embed(text: str) -> List[float]:
    """Return the embedding generated locally or via API.

    Args:
        text: The text to embed

    Returns:
        A list of floats representing the embedding vector

    Raises:
        RuntimeError: If generation fails
    """
    if USE_LOCAL_EMBEDDING:
        try:
            model = _get_local_model()
            if model:
                # SentenceTransformer returns numpy array, convert to list
                vector = model.encode(text).tolist()
                return vector
            else:
                print("Local model not available. Falling back to API.")
        except Exception as e:
            print(f"Local embedding failed: {e}. Falling back to API.")
            # Fallback to API flow below
            pass

    try:
        response = requests.post(
            EMBEDDING_URL, json={"model": EMBEDDING_MODEL, "input": text}, timeout=60
        )
        response.raise_for_status()
        data = response.json()
        vector = data["data"][0]["embedding"]
        return list(vector)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not connect to LM Studio at {EMBEDDING_URL}.\n"
            "PLEASE ENSURE:\n"
            "1. LM Studio is open.\n"
            "2. The 'Local Server' (double arrow icon <->) is selected.\n"
            "3. The green 'Start Server' button is clicked.\n"
            "4. The port is set to 1234."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to get embedding from API: {e}")


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a batch of texts.

    Args:
        texts: List of strings to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    if USE_LOCAL_EMBEDDING:
        # Local model handles batching natively and efficiently
        try:
            model = _get_local_model()
            if model:
                vectors = model.encode(texts).tolist()
                return vectors
        except Exception as e:
            print(f"Local batch embedding failed: {e}. Falling back to API.")
            pass

    # API Batching
    # Try sending the list directly (OpenAI API compatible)
    try:
        response = requests.post(
            EMBEDDING_URL, json={"model": EMBEDDING_MODEL, "input": texts}, timeout=120
        )
        response.raise_for_status()
        data = response.json()

        # OpenAI format returns a list of objects, we need to sort by index to be safe
        # though usually they are in order.
        embeddings_data = data["data"]
        # Sort by index just in case
        embeddings_data.sort(key=lambda x: x["index"])

        return [item["embedding"] for item in embeddings_data]

    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not connect to LM Studio at {EMBEDDING_URL}.")
    except Exception as e:
        # If batching fails (e.g. API doesn't support list input), fallback to sequential/parallel
        # But LM Studio usually supports it.
        print(f"Batch API failed ({e}), falling back to sequential...")
        return [embed(t) for t in texts]
