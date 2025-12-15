import os
from dataclasses import dataclass
from typing import Any, Dict, List

from .helper.llm_handler import generate_response
from .vector_query import search
from db.neo4j.neo4j_handler import query_graph


@dataclass(slots=True)
class ContextBundle:
    full_context: List[str]
    vector_hits: List[Dict[str, Any]]
    graph_context: List[str]


def llm_generate(prompt: str) -> str:
    """Generate a response using the local LLM.

    Args:
        prompt: The prompt text to send to the model

    Returns:
        The generated response text or an error message
    """
    try:
        return generate_response(prompt)
    except Exception as e:
        return f"Error generating response with the model gateway: {e}"


def get_graph_context(ids: List[int]) -> List[str]:
    """Retrieve graph context for a list of node IDs.

    Args:
        ids: List of node IDs to query

    Returns:
        List of text strings describing the graph relationships
    """
    if not ids:
        return []

    # Query for direct relationships of the found nodes
    # We use a Cypher query that formats the output as a readable string
    # We assume 'id' property in Neo4j matches the Milvus ID
    cypher = """
    MATCH (n)-[r]-(m)
    WHERE elementId(n) IN $ids
    RETURN 
        coalesce(n.name, 'Entity') + ' ' + type(r) + ' ' + coalesce(m.name, 'Entity') as desc
    LIMIT 20
    """
    
    try:
        results = query_graph(cypher, {"ids": ids})
        return [row["desc"] for row in results if row.get("desc")]
    except Exception as e:
        print(f"Error querying graph context: {e}")
        return []


def build_context_bundle(query: str, top_k: int = 5) -> ContextBundle:
    """Retrieve context plus debug artifacts for a query."""

    results = search(query, limit=top_k, return_raw=True)

    vector_context: List[str] = []
    node_ids: List[int] = []

    for row in results:
        text = row.get("text")
        nid = row.get("id")
        if isinstance(text, str):
            vector_context.append(text)
        if nid is not None:
            node_ids.append(nid)

    graph_context = get_graph_context(node_ids)
    full_context = vector_context + ["--- GRAPH CONNECTIONS ---"] + graph_context

    return ContextBundle(
        full_context=full_context,
        vector_hits=results,
        graph_context=graph_context,
    )


def build_context(query: str, top_k: int = 5) -> List[str]:
    """Backward-compatible helper returning only the merged context list."""

    return build_context_bundle(query, top_k).full_context


def build_prompt(query: str, context: List[str]) -> str:
    """Build a RAG prompt with context and query.

    Args:
        query: The user's question
        context: List of relevant document texts

    Returns:
        Formatted prompt string for the LLM
    """
    context = "\n\n--- DOCUMENT ---\n\n".join(context)

    return f"""
You are an expert assistant for music datasets.

You MUST respond in the SAME language as the user's question.
- If the question is in Spanish, respond entirely in Spanish.
- If the question is in English, respond entirely in English.
- Match the user's language exactly.

Use only the following context to answer:

{context}

Question: {query}

Answer (in the same language as the question):
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
    return llm_generate(prompt)
