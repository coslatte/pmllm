import os
import requests
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_lm_studio_connection():
    """Test connection to LM Studio API and model availability."""
    url = os.getenv("EMBEDDING_URL", "http://localhost:1234/v1/embeddings")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat")
    
    # Check if server is up (using models endpoint)
    base_url = url.rsplit('/', 2)[0] # http://localhost:1234/v1
    try:
        response = requests.get(f"{base_url}/models", timeout=5)
        assert response.status_code == 200, f"LM Studio models endpoint returned {response.status_code}"
        
        data = response.json()
        model_ids = [m['id'] for m in data['data']]
        print(f"\nAvailable models: {model_ids}")
        
        # Warn if configured model is not exactly found (might be okay if it's an alias, but good to know)
        if model not in model_ids:
            print(f"Warning: Configured model '{model}' not found in LM Studio list. Available: {model_ids}")
            
    except requests.exceptions.ConnectionError:
        pytest.fail("Could not connect to LM Studio. Is it running on port 1234?")

def test_embedding_generation():
    """Test generating a single embedding."""
    url = os.getenv("EMBEDDING_URL", "http://localhost:1234/v1/embeddings")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat")
    
    payload = {
        "model": model,
        "input": "Test string for embedding"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        assert response.status_code == 200, f"Embedding failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        assert "embedding" in data["data"][0]
        embedding = data["data"][0]["embedding"]
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        print(f"\nSuccess! Generated embedding of length {len(embedding)}")
        
    except requests.exceptions.ConnectionError:
        pytest.fail("Could not connect to LM Studio for embedding generation.")
