import os
from typing import Any, List
import sys

# We will use sentence-transformers locally to avoid LM Studio memory conflicts
# and to speed up batch processing.
from sentence_transformers import SentenceTransformer

# Path or name of the model. If you downloaded it via LM Studio, you might need to point
# to the specific folder, or just let sentence-transformers download its own copy (cache).
# For Qwen embedding, usually "Alibaba-NLP/gte-Qwen2-1.5B-instruct" or similar is used.
# Since you mentioned "text-embedding-qwen3-embedding-0.6b", we'll use a placeholder
# that you should update if you have a local path.
# If you want to use the exact model file from LM Studio, provide the absolute path.
MODEL_NAME = os.getenv("EMBEDDING_MODEL_PATH", "Alibaba-NLP/gte-Qwen2-1.5B-instruct")

# Load model once (global)
print(f"Loading embedding model: {MODEL_NAME}...")
_model = None
try:
    _model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
    print(f"Successfully loaded model: {MODEL_NAME}")
except Exception as e:
    print(f"Error loading model {MODEL_NAME}: {e}", file=sys.stderr)
    print("Falling back to 'all-MiniLM-L6-v2' for testing purposes.", file=sys.stderr)
    try:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("Successfully loaded fallback model 'all-MiniLM-L6-v2'")
    except Exception as fallback_error:
        print(f"CRITICAL: Failed to load fallback model: {fallback_error}", file=sys.stderr)
        raise


def embed(text: str) -> List[float]:
    """Return the embedding generated locally by sentence-transformers.
    
    Args:
        text: The text to embed
        
    Returns:
        A list of floats representing the embedding vector
        
    Raises:
        RuntimeError: If the model failed to load
    """
    if _model is None:
        raise RuntimeError("Embedding model failed to load. Cannot generate embeddings.")
    vector: Any = _model.encode(text, normalize_embeddings=True)

    if hasattr(vector, "tolist"):
        return list(vector.tolist())  # type: ignore[arg-type]

    if isinstance(vector, (list, tuple)):
        return list(vector)

    # Fallback for unexpected types (e.g., numpy array without tolist)
    return [float(v) for v in vector]  # type: ignore[call-arg]
