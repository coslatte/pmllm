from db.neo4j.neo4j_handler import stream_nodes
from helper.text_builder import build_text
from helper.embedder import embed
from milvus_store import init_milvus


def populate(labels):
    collection = init_milvus()

    for label in labels:
        print(f"Processing label: {label}")

        ids = []
        embeddings = []
        texts = []
        node_labels = []

        for node in stream_nodes(label):
            text = build_text(node)
            vector = embed(text)

            ids.append(node["id"])
            embeddings.append(vector)
            texts.append(text)
            node_labels.append(label)

        if ids:
            print(f"Inserting {len(ids)} nodes for {label}...")
            collection.insert([ids, embeddings, texts, node_labels])
            collection.flush()

    print("Vector DB build completed successfully.")
