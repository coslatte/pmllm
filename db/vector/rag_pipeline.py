from vector_query import search
import os
import requests


QWEN_GENERATE_URL = os.getenv("QWEN_GENERATE_URL", "http://localhost:11434/api/generate")
QWEN_GENERATE_MODEL = os.getenv("QWEN_GENERATE_MODEL", "qwen/qwen3-1.7b")


def qwen_generate(prompt: str) -> str:
    response = requests.post(
        QWEN_GENERATE_URL,
        json={"model": QWEN_GENERATE_MODEL, "prompt": prompt, "stream": False},
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def build_context(query: str, top_k: int = 5):
    results = search(query, limit=top_k, return_raw=True)
    return [r["text"] for r in results]


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
