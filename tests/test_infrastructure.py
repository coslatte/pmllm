from __future__ import annotations

import os

import pytest
import requests
from dotenv import load_dotenv


load_dotenv()


def _headers() -> dict[str, str]:
    token = os.getenv("MODEL_API_KEY") or os.getenv("LLM_API_KEY")
    return {"Authorization": f"Bearer {token}"} if token else {}


def test_embedding_api_connection():
    """Ensure the embedding endpoint in the model gateway is reachable."""

    url = (
        os.getenv("EMBEDDING_API_URL")
        or os.getenv("EMBEDDING_URL")
        or "http://localhost:9000/v1/embeddings"
    )
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat")
    payload = {"model": model, "input": "Ping from infrastructure test"}

    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=10)
    except requests.exceptions.ConnectionError as exc:
        pytest.fail(f"Could not connect to the embedding API: {exc}")

    assert response.status_code == 200, (
        f"Embedding API returned {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "data" in body and body["data"], "Embedding API response missing vectors"
    vector = body["data"][0].get("embedding", [])
    assert isinstance(vector, list) and vector, "Embedding payload missing numeric array"


def test_llm_api_connection():
    """Smoke test the chat-completions endpoint exposed by the model gateway."""

    url = os.getenv("LLM_API_URL", "http://localhost:9000/v1/chat/completions")
    model = os.getenv("LLM_MODEL", "gemma-3-1b-it-qat")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Say hello concisely."},
            {"role": "user", "content": "ping"},
        ],
        "max_tokens": 8,
        "temperature": 0.2,
    }

    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=10)
    except requests.exceptions.ConnectionError as exc:
        pytest.fail(f"Could not connect to the LLM API: {exc}")

    assert response.status_code == 200, (
        f"LLM API returned {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "choices" in body and body["choices"], "LLM API response missing choices"
