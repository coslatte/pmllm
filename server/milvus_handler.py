import os
import sys
import time
from typing import Dict, Any, Optional
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)

# Add project root to sys.path to allow imports from db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.vector.helper.embedder import embed

COLLECTION_NAME = "user_profile_vectors"
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")


async def get_milvus_collection() -> Collection:
    """Connects to Milvus and returns the user profile collection."""

    # Connect if not connected
    try:
        if not connections.has_connection("default"):
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception:
        # Retry or just try connecting
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)

    # Define schema
    if not utility.has_collection(COLLECTION_NAME):
        fields = [
            FieldSchema(
                name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True
            ),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=5000),
            FieldSchema(
                name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768
            ),  # Assuming 768 dim from embedder
            FieldSchema(name="updated_at", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields, description="User profile embeddings")
        collection = Collection(COLLECTION_NAME, schema)

        # Create index
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        collection.create_index("embedding", index_params)
    else:
        collection = Collection(COLLECTION_NAME)

        collection.load()
    return collection


async def upsert_user_profile(user_id: str, profile_text: str):
    """Generates embedding for profile text and upserts into Milvus."""
    collection = await get_milvus_collection()

    # Generate embedding
    vector = embed(profile_text)

    # Current timestamp
    timestamp = int(time.time())

    # Data to insert/upsert
    # Milvus upsert replaces data with same PK
    data = [
        [user_id],  # id
        [profile_text],  # text
        [vector],  # embedding
        [timestamp],  # updated_at
    ]

    collection.upsert(data)
    # Flush to ensure visibility (optional but good for immediate read)
    collection.flush()


async def get_user_profile_vector(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the user profile vector and text from Milvus."""
    collection = await get_milvus_collection()

    res = collection.query(
        expr=f"id == '{user_id}'", output_fields=["text", "embedding", "updated_at"]
    )

    if res:
        return res[0]
    return None
