import os
from typing import Any, Dict, List

import requests

from .vector_query import search


QWEN_GENERATE_URL = os.getenv("QWEN_GENERATE_URL", "http://localhost:1234/v1/chat/completions")
QWEN_GENERATE_MODEL = os.getenv("QWEN_GENERATE_MODEL", "qwen-1.7b")  # Name used in LM Studio


def qwen_generate(prompt: str) -> str:
    # LM Studio uses OpenAI-compatible API structure
    payload = {
        "model": QWEN_GENERATE_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful music expert assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        response = requests.post(QWEN_GENERATE_URL, json=payload, timeout=30)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        choice_list = data.get("choices")
        if not isinstance(choice_list, list) or not choice_list:
            raise ValueError("LLM response missing choices list")
        first_choice = choice_list[0]
        if not isinstance(first_choice, dict):
            raise ValueError("LLM response choice is malformed")
        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            raise ValueError("LLM response message is malformed")
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("LLM response content missing")
        return content
    except Exception as e:
        return f"Error generating response: {e}"


def build_context(query: str, top_k: int = 5) -> List[str]:
    results = search(query, limit=top_k, return_raw=True)
    context: List[str] = []
    for row in results:
        text = row.get("text") if isinstance(row, dict) else None
        if isinstance(text, str):
            context.append(text)
    return context


def build_prompt(query: str, context: list[str]) -> str:
    ctx = "\n\n--- DOCUMENTO ---\n\n".join(context)

    return f"""
You are an expert assistant for music datasets.
Answer using only the following context:

{ctx}

Question: {query}

Answer:
"""


def rag_answer(query: str, k: int = 5) -> str:
    context = build_context(query, k)

    if not context:
        return "No relevant context found in the vector database."

    prompt = build_prompt(query, context)
    return qwen_generate(prompt)
