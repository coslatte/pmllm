from milvus_store import init_milvus
from helper.embedder import embed


def search(query, limit=5, return_raw=False):
    col = init_milvus()
    qvec = embed(query)

    results = col.search(
        data=[qvec],
        anns_field="embedding",
        limit=limit,
        output_fields=["text", "label"],
    )

    if return_raw:
        return [
            {
                "text": hit.entity.get("text"),
                "label": hit.entity.get("label"),
                "score": hit.distance,
            }
            for hit in results[0]
        ]

    # Modo impresión previa (como ya lo tienes)
    for hit in results[0]:
        print(f"[score={hit.distance:.4f}] ({hit.entity.get('label')})")
        print(hit.entity.get("text"))
        print("-" * 40)
