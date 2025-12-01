import os
from typing import Any, Dict, List

from .helper.llm_handler import generate_response
from .vector_query import search
from db.neo4j.neo4j_handler import query_graph


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
        return f"Error generating response with local LLM: {e}"


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
        coalesce(n.name, n.title, 'Entity') + ' ' + type(r) + ' ' + coalesce(m.name, m.title, 'Entity') as desc
    LIMIT 20
    """
    
    try:
        results = query_graph(cypher, {"ids": ids})
        return [row["desc"] for row in results if row.get("desc")]
    except Exception as e:
        print(f"Error querying graph context: {e}")
        return []


def build_context(query: str, top_k: int = 5) -> List[str]:
    """Retrieve relevant context documents for a query.

    Args:
        query: The search query
        top_k: Number of top results to retrieve (default: 5)

    Returns:
        List of text strings from relevant documents
    """
    # 1. Vector Search
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
            
    # 2. Graph Search (using IDs from vector search)
    graph_context = get_graph_context(node_ids)
    
    # Combine contexts
    full_context = vector_context + ["--- GRAPH CONNECTIONS ---"] + graph_context
    return full_context


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
    return llm_generate(prompt)
