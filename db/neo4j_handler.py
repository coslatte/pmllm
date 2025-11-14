# archivo: neo4j_extract.py
import os
from neo4j import GraphDatabase
from typing import Generator, Dict, Any, List

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def close():
    driver.close()


def list_labels_and_reltypes():
    """Devuelve las labels y tipos de relación presentes en la DB."""
    with driver.session() as session:
        labels = session.run("CALL db.labels()").value()
        reltypes = session.run("CALL db.relationshipTypes()").value()
    return labels, reltypes


def node_to_dict(record) -> Dict[str, Any]:
    """Convierte un nodo/registro neo4j a dict plano (id, labels, props)."""
    node = record  # expects a neo4j.Node-like mapping
    # Si recibes un Row con key 'n', entonces usa row['n'] al llamar
    try:
        nid = node.id
        labels = list(node.labels)
        props = dict(node)
    except Exception:
        # Si el record viene como Row con 'n'
        nid = node["n"].id
        labels = list(node["n"].labels)
        props = dict(node["n"])
    return {"id": nid, "labels": labels, "props": props}


def stream_nodes(
    label: str, batch: int = 1000
) -> Generator[Dict[str, Any], None, None]:
    """
    Itera sobre nodos con una label determinada de forma escalable.
    Usa SKIP/LIMIT para batching simple (funciona bien para learning / datasets medianos).
    Para datasets grandes usar apoc.periodic.iterate en el servidor.
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
                # r["n"] es el nodo
                yield node_to_dict(r["n"])
            offset += batch


def fetch_all_nodes_for_labels(
    labels: List[str], batch: int = 1000
) -> Dict[str, List[Dict[str, Any]]]:
    """Recupera nodos para cada label de la lista y los devuelve en un dict."""
    out = {}
    for lab in labels:
        out[lab] = []
        for node in stream_nodes(lab, batch=batch):
            out[lab].append(node)
    return out


# Ejemplo de uso directo
if __name__ == "__main__":
    labels, reltypes = list_labels_and_reltypes()
    print("Labels en la DB:", labels)
    print("Tipos de relación:", reltypes)

    # Si tus labels son exactamente Artist, Recording, Release, Tag, ArtistCredit
    target_labels = ["Artist", "Recording", "Release", "Tag", "ArtistCredit"]
    # Comprueba qué labels existen realmente y filtra
    existing = [lab for lab in target_labels if lab in labels]
    print("Labels objetivo existentes:", existing)

    # Extraer ejemplo para Artist (primera página)
    print("Mostrando 5 artistas de ejemplo:")
    for i, node in enumerate(stream_nodes("Artist", batch=100)):
        if i >= 5:
            break
        print(node)
    # Cierra driver al terminar
    close()
