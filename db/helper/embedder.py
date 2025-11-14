from sentence_transformers import SentenceTransformer

# Modelo rápido y de buena calidad para RAG
model = SentenceTransformer("all-mpnet-base-v2")  # 768 dims


def embed(text: str):
    return model.encode(text).tolist()
