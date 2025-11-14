from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection


def init_milvus(db_path="milvus.db", dim=768):
    connections.connect("default", uri=db_path)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="label", dtype=DataType.VARCHAR, max_length=100),
    ]

    schema = CollectionSchema(fields)

    try:
        collection = Collection("musicbrainz", schema)
    except Exception:
        collection = Collection("musicbrainz")

    # index
    index = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 16, "efConstruction": 200},
    }
    collection.create_index("embedding", index)

    return collection
