def build_text(node: dict) -> str:
    """
    Receive a dict {"id", "labels", "props"}
    and render a text snippet for embedding using its properties.
    """

    labels = node["labels"]
    props = node["props"]

    txt = []

    # main label
    title = labels[0] if labels else "Entity"
    txt.append(f"{title}:")

    # key properties
    for k, v in props.items():
        # Avoid Python-style list serialization; use comma-separated text
        if isinstance(v, list):
            v = ", ".join(map(str, v))
        txt.append(f"{k}: {v}")

    return "\n".join(txt)
