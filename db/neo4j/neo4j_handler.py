import atexit
import math
import os
from neo4j import GraphDatabase
from typing import Generator, Dict, Any, List
import warnings
import logging

# warnings.filterwarnings("ignore", message=".*id is deprecated.*")
# logging.getLogger("neo4j").setLevel(logging.ERROR)
# logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

# sampling helpers
_SAMPLE_MOD_BASE = 10000
_SAMPLE_HASH_EXPR = "toInteger(coalesce(last(split(elementId(n), ':')), elementId(n)))"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# For development/testing only - set NEO4J_ALLOW_INSECURE=true to use default password
_allow_insecure = os.getenv("NEO4J_ALLOW_INSECURE", "").lower() == "true"

if not NEO4J_PASSWORD:
    if _allow_insecure:
        warnings.warn(
            "Using default Neo4j password 'neo4j' because NEO4J_ALLOW_INSECURE=true. "
            "This is ONLY for development/testing. Never use in production!",
            UserWarning,
            stacklevel=2,
        )
        NEO4J_PASSWORD = "neo4j"
    else:
        # Don't raise error at import time, only when trying to connect
        NEO4J_PASSWORD = None

_driver = None


def _validate_demo_mode():
    """Validate that demo mode uses appropriate sampling."""
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if demo_mode:
        sample_percent = float(os.getenv("SAMPLE_PERCENT", "100.0"))
        if sample_percent >= 1.0:
            warnings.warn(
                "DEMO_MODE is enabled but SAMPLE_PERCENT is >= 1.0%. "
                "Consider setting SAMPLE_PERCENT=0.1 for faster demo builds."
            )

def _get_driver():
    """Get or create the Neo4j driver."""
    global _driver
    if _driver is None:
        _validate_demo_mode()
        if not NEO4J_PASSWORD:
            raise ValueError(
                "NEO4J_PASSWORD environment variable must be set. "
                "For development/testing only, you can set NEO4J_ALLOW_INSECURE=true "
                "to use the default password (NOT recommended for production)."
            )
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver

def close():
    """Close the Neo4j driver connection."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None


atexit.register(close)


def list_labels_and_reltypes():
    """Return the labels and relationship types present in the database."""
    driver = _get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
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
        try:
            nid = node.elementId
        except AttributeError:
            nid = node.id
        labels = list(node.labels)
        props = dict(node)
    except (AttributeError, TypeError):
        # If the record is a Row containing key 'n'
        try:
            try:
                nid = node["n"].elementId
            except AttributeError:
                nid = node["n"].id
            labels = list(node["n"].labels)
            props = dict(node["n"])
        except (KeyError, AttributeError, TypeError) as e:
            raise ValueError(f"Invalid node/record format: {e}") from e
    return {"id": nid, "labels": labels, "props": props}


def _clamp_sample_percent(sample_percent: float) -> float:
    return max(0.0, min(sample_percent, 100.0))


def _build_sample_clause(sample_percent: float) -> str:
    percent = _clamp_sample_percent(sample_percent)
    if percent >= 100.0:
        return ""
    threshold = int(math.floor(percent / 100.0 * _SAMPLE_MOD_BASE))
    threshold = max(0, min(threshold, _SAMPLE_MOD_BASE))
    return (
        f"WHERE ({_SAMPLE_HASH_EXPR} % {_SAMPLE_MOD_BASE}) < {threshold}"
        if threshold > 0
        else f"WHERE ({_SAMPLE_HASH_EXPR} % {_SAMPLE_MOD_BASE}) < 0"
    )


def count_nodes(label: str, sample_percent: float | None = None) -> int:
    """Return the total number of nodes for a label (optionally sampled)."""
    driver = _get_driver()
    where_clause = ""
    if sample_percent is not None:
        where_clause = _build_sample_clause(sample_percent)
    query = f"MATCH (n:{label}) {where_clause} RETURN count(n) AS total"
    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.run(query).single()  # type: ignore[arg-type]
        return int(record["total"]) if record and record["total"] is not None else 0


def stream_nodes(
    label: str, batch: int = 1000, sample_percent: float = 100.0
) -> Generator[Dict[str, Any], None, None]:
    """
    Iterate over nodes with a given label using SKIP/LIMIT batching.
    Supports sampling via random filtering.
    """
    driver = _get_driver()
    offset = 0
    max_iterations = 100000  # Safety limit to prevent infinite loops
    iteration = 0
    
    where_clause = _build_sample_clause(sample_percent)
    if where_clause:
        where_clause = f"{where_clause}\n"

    while iteration < max_iterations:
        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                # Query using SKIP/LIMIT for pagination (elementId is string, not suitable for > comparison)
                query = f"MATCH (n:{label}) {where_clause}RETURN n SKIP $offset LIMIT $batch"
                result = session.run(query, offset=offset, batch=batch)  # type: ignore[arg-type]
                
                count = 0
                batch_nodes = list(result) # Consume result eagerly
                
                if not batch_nodes:
                    break
                    
                for record in batch_nodes:
                    node_data = node_to_dict(record)
                    yield node_data
                    count += 1
                
                if count < batch:
                    break
                
                offset += count
                iteration += 1
        except Exception as e:
            print(f"Error streaming nodes for {label} at offset={offset}: {e}")
            raise e
    
    if iteration >= max_iterations:
        print(f"Warning: Reached max iterations ({max_iterations}) for {label}, stopping to prevent infinite loop")

def query_graph(cypher_query: str, params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    """Execute a Cypher query and return the results as a list of dictionaries.

    Args:
        cypher_query: The Cypher query string
        params: Dictionary of parameters for the query

    Returns:
        List of dictionaries representing the records
    """
    driver = _get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher_query, parameters=params)  # type: ignore
        return [record.data() for record in result]


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
