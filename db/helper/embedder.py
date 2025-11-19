from sentence_transformers import SentenceTransformer

# Fast, high-quality sentence embedding model for RAG
model = SentenceTransformer("all-mpnet-base-v2")  # 768 dims


def embed(text: str):
    return model.encode(text).tolist()
