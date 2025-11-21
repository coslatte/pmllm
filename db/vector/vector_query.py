from .milvus_store import init_milvus
from .helper.embedder import embed


def search(query, limit=5, return_raw=False):
    """Search the Milvus vector database for similar documents.

    Args:
        query: The search query text
        limit: Maximum number of results to return (default: 5)
        return_raw: If True, return raw results list instead of printing (default: False)

    Returns:
        List of hit dictionaries containing text, label, and score
    """
    col = init_milvus()
    qvec = embed(query)

    results = col.search(
        data=[qvec],
        anns_field="embedding",
        limit=limit,
        output_fields=["text", "label"],
    )

    hits = [
        {
            "text": hit.entity.get("text"),
            "label": hit.entity.get("label"),
            "score": hit.distance,
        }
        for hit in results[0]
    ]

    if return_raw:
        return hits

    for hit in hits:
        print(f"[score={hit['score']:.4f}] ({hit['label']})")
        print(hit["text"])
        print("-" * 40)

    return hits
