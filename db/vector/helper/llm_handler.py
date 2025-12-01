import os
from typing import Any, Dict

import requests

# Configuration for the model gateway
LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:9000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma-3-1b-it-qat")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("MODEL_API_KEY")
LLM_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "512"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_API_TIMEOUT = float(os.getenv("LLM_API_TIMEOUT", "120"))


def _build_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    return headers


def _extract_text_choice(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not choices:
        raise RuntimeError("LLM response did not contain 'choices'.")

    first = choices[0]
    if "message" in first:
        content = first["message"].get("content")
    else:
        content = first.get("text")

    if not content:
        raise RuntimeError("LLM response did not include any text content.")
    return content.strip()


def generate_response(
    prompt: str, system_message: str = "You are a helpful music expert assistant."
) -> str:
    """Generate a response using the configured model gateway."""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": LLM_MAX_NEW_TOKENS,
        "temperature": LLM_TEMPERATURE,
        "stream": False,
    }

    response = requests.post(
        LLM_API_URL,
        json=payload,
        headers=_build_headers(),
        timeout=LLM_API_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return _extract_text_choice(data)