from db.neo4j.neo4j_handler import stream_nodes
from .helper.text_builder import build_text
from .helper.embedder import embed
from .milvus_store import init_milvus

# Milvus VARCHAR field limit for text storage
MAX_TEXT_LENGTH = 2000
TRUNCATION_SUFFIX = "..."


def truncate_text(
    text: str, max_length: int = MAX_TEXT_LENGTH, suffix: str = TRUNCATION_SUFFIX
) -> str:
    """Truncate text to fit within a maximum length.

    Args:
        text: The text to truncate
        max_length: Maximum allowed length (default: MAX_TEXT_LENGTH)
        suffix: Suffix to add when truncating (default: TRUNCATION_SUFFIX)

    Returns:
        Truncated text with suffix if needed, otherwise original text
    """
    if len(text) > max_length:
        return text[: max_length - len(suffix)] + suffix
    return text


def populate(labels):
    """Populate the Milvus vector database with nodes from Neo4j.

    Args:
        labels: List of Neo4j node labels to process and embed
    """
    collection = init_milvus()

    for label in labels:
        print(f"Processing label: {label}")

        ids = []
        embeddings = []
        texts = []
        node_labels = []

        for node in stream_nodes(label):
            text = build_text(node)
            # Truncate text to fit VARCHAR max_length limit
            text = truncate_text(text)

            try:
                vector = embed(text)

                ids.append(node["id"])
                embeddings.append(vector)
                texts.append(text)
                node_labels.append(label)
            except (RuntimeError, ValueError) as e:
                # Model loading or embedding generation errors
                print(f"Warning: Failed to embed node {node['id']}: {e}")
                continue
            except Exception as e:
                # Unexpected errors - log and continue but notify
                print(
                    f"Error: Unexpected error embedding node {node['id']}: {type(e).__name__}: {e}"
                )
                continue

        if ids:
            print(f"Inserting {len(ids)} nodes for {label}...")
            try:
                collection.insert([ids, embeddings, texts, node_labels])
                collection.flush()
                print(f"Successfully inserted {len(ids)} nodes for {label}")
            except Exception as e:
                print(f"Error inserting nodes for {label}: {e}")

    print("Vector DB build completed.")
