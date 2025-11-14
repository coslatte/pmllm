def build_text(node: dict) -> str:
    """
    Recibe un dict {"id", "labels", "props"}
    y genera un texto para embedding basado en las propiedades.
    """

    labels = node["labels"]
    props = node["props"]

    txt = []

    # etiqueta principal
    title = labels[0] if labels else "Entity"
    txt.append(f"{title}:")

    # propiedades principales
    for k, v in props.items():
        # Evitar serializar listas como Python → pasarlas a CSV
        if isinstance(v, list):
            v = ", ".join(map(str, v))
        txt.append(f"{k}: {v}")

    return "\n".join(txt)
