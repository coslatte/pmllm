from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
from typing import Optional, Union


def init_milvus(
    alias: str = "default",
    uri: Optional[str] = None,
    host: str = "127.0.0.1",
    port: Union[str, int] = "19530",
    dim: int = 768,
):
    """Connect to Milvus and return (or create) the musicbrainz collection."""

    if uri:
        connections.connect(alias, uri=uri)
    else:
        connections.connect(alias, host=host, port=str(port))

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="label", dtype=DataType.VARCHAR, max_length=100),
    ]

    schema = CollectionSchema(fields)

    try:
        collection = Collection("musicbrainz", schema, using=alias)
    except Exception:
        collection = Collection("musicbrainz", using=alias)

    # Create index if it doesn't exist
    index = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 16, "efConstruction": 200},
    }
    
    # Check if index already exists before creating
    try:
        if not collection.has_index():
            collection.create_index("embedding", index)
    except Exception as e:
        # Index might already exist, which is fine
        pass

    return collection
