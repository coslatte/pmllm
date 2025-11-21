import os
from typing import Any, Dict, List

import requests

from .vector_query import search


QWEN_GENERATE_URL = os.getenv("QWEN_GENERATE_URL", "http://localhost:1234/v1/chat/completions")
QWEN_GENERATE_MODEL = os.getenv("QWEN_GENERATE_MODEL", "qwen-1.7b")  # Name used in LM Studio


def qwen_generate(prompt: str) -> str:
    """Generate a response using the Qwen LLM via LM Studio API.
    
    Args:
        prompt: The prompt text to send to the model
        
    Returns:
        The generated response text or an error message
    """
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
    except requests.exceptions.RequestException as e:
        return f"Error connecting to LLM service: {e}"
    except (KeyError, IndexError) as e:
        return f"Error parsing LLM response: {e}"
    except Exception as e:
        return f"Unexpected error generating response: {e}"


def build_context(query: str, top_k: int = 5) -> List[str]:
    """Retrieve relevant context documents for a query.
    
    Args:
        query: The search query
        top_k: Number of top results to retrieve (default: 5)
        
    Returns:
        List of text strings from relevant documents
    """
    results = search(query, limit=top_k, return_raw=True)
    context: List[str] = []
    for row in results:
        text = row.get("text") if isinstance(row, dict) else None
        if isinstance(text, str):
            context.append(text)
    return context


def build_prompt(query: str, context: List[str]) -> str:
    """Build a RAG prompt with context and query.
    
    Args:
        query: The user's question
        context: List of relevant document texts
        
    Returns:
        Formatted prompt string for the LLM
    """
    ctx = "\n\n--- DOCUMENTO ---\n\n".join(context)

    return f"""
You are an expert assistant for music datasets.
Answer using only the following context:

{ctx}

Question: {query}

Answer:
"""


def rag_answer(query: str, k: int = 5) -> str:
    """Answer a query using RAG (Retrieval-Augmented Generation).
    
    Args:
        query: The user's question
        k: Number of context documents to retrieve (default: 5)
        
    Returns:
        Generated answer based on retrieved context
    """
    context = build_context(query, k)

    if not context:
        return "No relevant context found in the vector database."

    prompt = build_prompt(query, context)
    return qwen_generate(prompt)
