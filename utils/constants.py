import typer


SUCCESS = typer.colors.GREEN
ERROR = typer.colors.RED
INFO = typer.colors.BLUE

DEFAULT_VECTOR_LABELS = [
    "Artist",
    "Recording",
    "Release",
    "ReleaseGroup",
    "Work",
    "Area",
    "Tag",
    "ArtistCredit",
    "Label",
    "Medium",
    "Track",
    "Place",
    "Event",
    "Genre",
    "Instrument",
    "Series",
    "Url",
]

CRITICAL_ENV_VARS = [
    "NEO4J_BIN_PATH",
    "JAVA_HOME",
    "NEO4J_DATA_DIR",
    "DB_NAME",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_DATABASE",
    "NEO4J_HOST",
    "NEO4J_PORT",
    "MILVUS_HOST",
    "MILVUS_PORT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "LLM_API_URL",
    "LLM_MODEL",
    "EMBEDDING_MODEL",
    "EMBEDDING_API_URL",
    "OUTPUT_DIR",
    "TSV_CORE_DIR",
    "TSV_DERIVED_DIR",
    "CSV_CORE_DIR",
    "CSV_DERIVED_DIR",
]
