from vector_query import search
import requests


def gemma_generate(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",  # Port exposed by Ollama
        json={"model": "gemma3:12b", "prompt": prompt, "stream": False},
    )
    data = response.json()
    return data["response"]


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
    return gemma_generate(prompt)
