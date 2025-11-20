import os
from neo4j import GraphDatabase
from typing import Generator, Dict, Any, List, Optional
import warnings


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# For development/testing only - set NEO4J_ALLOW_INSECURE=true to use default password
_allow_insecure = os.getenv("NEO4J_ALLOW_INSECURE", "").lower() == "true"

if not NEO4J_PASSWORD:
    if _allow_insecure:
        warnings.warn(
            "Using default Neo4j password 'neo4j' because NEO4J_ALLOW_INSECURE=true. "
            "This is ONLY for development/testing. Never use in production!",
            UserWarning,
            stacklevel=2
        )
        NEO4J_PASSWORD = "neo4j"
    else:
        raise ValueError(
            "NEO4J_PASSWORD environment variable must be set. "
            "For development/testing only, you can set NEO4J_ALLOW_INSECURE=true "
            "to use the default password (NOT recommended for production)."
        )

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def close():
    """Close the Neo4j driver connection."""
    driver.close()


def list_labels_and_reltypes():
    """Return the labels and relationship types present in the database."""
    with driver.session() as session:
        labels = session.run("CALL db.labels()").value()
        reltypes = session.run("CALL db.relationshipTypes()").value()
    return labels, reltypes


def node_to_dict(record) -> Dict[str, Any]:
    """Normalize a Neo4j node/record into a dict with id, labels, and props.
    
    Args:
        record: A Neo4j node or record object
        
    Returns:
        Dictionary with 'id', 'labels', and 'props' keys
    """
    node = record  # expects a neo4j.Node-like mapping
    # When receiving a Record with key 'n', access row['n']
    try:
        nid = node.id
        labels = list(node.labels)
        props = dict(node)
    except (AttributeError, TypeError):
        # If the record is a Row containing key 'n'
        try:
            nid = node["n"].id
            labels = list(node["n"].labels)
            props = dict(node["n"])
        except (KeyError, AttributeError, TypeError) as e:
            raise ValueError(f"Invalid node/record format: {e}") from e
    return {"id": nid, "labels": labels, "props": props}


def stream_nodes(
    label: str, batch: int = 1000
) -> Generator[Dict[str, Any], None, None]:
    """
    Iterate over nodes with a given label using basic SKIP/LIMIT batching.
    Works for small/medium datasets; for very large datasets consider
    apoc.periodic.iterate running on the Neo4j server.
    """
    offset = 0
    with driver.session() as session:
        while True:
            q = f"MATCH (n:{label}) RETURN n SKIP $skip LIMIT $limit"
            result = session.run(q, skip=offset, limit=batch)
            rows = list(result)
            if not rows:
                break
            for r in rows:
                # r["n"] contains the node
                yield node_to_dict(r["n"])
            offset += batch


def fetch_all_nodes_for_labels(
    labels: List[str], batch: int = 1000
) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve nodes for each label and return them grouped in a dict."""
    out = {}
    for lab in labels:
        out[lab] = []
        for node in stream_nodes(lab, batch=batch):
            out[lab].append(node)
    return out


# Example direct usage
if __name__ == "__main__":
    labels, reltypes = list_labels_and_reltypes()
    print("Labels in the DB:", labels)
    print("Relationship types:", reltypes)

    # Illustrative list for common MusicBrainz labels
    target_labels = ["Artist", "Recording", "Release", "Tag", "ArtistCredit"]
    # Filter to the labels that actually exist in the database
    existing = [lab for lab in target_labels if lab in labels]
    print("Existing target labels:", existing)

    # Sample the first five Artist nodes
    print("Showing 5 sample artists:")
    for i, node in enumerate(stream_nodes("Artist", batch=100)):
        if i >= 5:
            break
        print(node)
    # Close the driver when finished
    close()
