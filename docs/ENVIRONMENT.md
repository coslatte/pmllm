# Overview

The pmllm system uses environment variables for all configuration. Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
# Edit .env with your specific values
```

## Variable Categories

### Neo4j Connection Settings

| Variable               | Default                 | Description                                                                             |
| ---------------------- | ----------------------- | --------------------------------------------------------------------------------------- |
| `NEO4J_URI`            | `bolt://localhost:7687` | Neo4j connection URI. Use `bolt://` for secure connections or `neo4j://` for clustering |
| `NEO4J_USER`           | `neo4j`                 | Neo4j database username                                                                 |
| `NEO4J_PASSWORD`       | `your_password_here`    | Neo4j database password. Required for authentication                                    |
| `NEO4J_DATABASE`       | `pmllmdb`               | Neo4j database name used by this project                                                |
| `NEO4J_ALLOW_INSECURE` | `false`                 | Allow connections with default password. Only for development/testing                   |
| `NEO4J_DATA_DIR`       | -                       | Path to Neo4j data directory for local bulk imports                                     |

### Milvus Vector Database Settings

| Variable      | Default     | Description                          |
| ------------- | ----------- | ------------------------------------ |
| `MILVUS_HOST` | `127.0.0.1` | Milvus server hostname or IP address |
| `MILVUS_PORT` | `19530`     | Milvus server port number            |

### MinIO Object Storage

| Variable           | Default      | Description                         |
| ------------------ | ------------ | ----------------------------------- |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key for authentication |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key for authentication |

**Security Warning:** Change MinIO credentials for production use!

### LLM API Settings

| Variable            | Default                                     | Description                                        |
| ------------------- | ------------------------------------------- | -------------------------------------------------- |
| `QWEN_GENERATE_URL` | `http://127.0.0.1:1234/v1/chat/completions` | Endpoint URL for LLM API (LM Studio or compatible) |
| `LLM_MODEL`         | `google/gemma-3-1b`                         | Model name to use for text generation              |

### Embedding Model Settings

| Variable               | Default                                  | Description                                                       |
| ---------------------- | ---------------------------------------- | ----------------------------------------------------------------- |
| `USE_LOCAL_EMBEDDING`  | `false`                                  | Use local SentenceTransformer instead of LM Studio embeddings API |
| `EMBEDDING_MODEL`      | `text-embedding-embeddinggemma-300m-qat` | Model name for embeddings (local or remote)                       |
| `EMBEDDING_MODEL_PATH` | `text-embedding-embeddinggemma-300m-qat` | Path to embedding model. Can be HuggingFace name or local path    |
| `EMBEDDING_URL`        | `http://127.0.0.1:1234/v1/embeddings`    | LM Studio embeddings endpoint URL                                 |

> **LM Studio workflow reminder:** the `build` command expects LM Studio to expose the embedding model during conversion, preparation, and vector creation. After the build completes you can switch LM Studio to the conversational LLM model for `query` runs.

## Build Process Configuration

### Input/Output Directories

| Variable          | Default                     | Description                                                                                     |
| ----------------- | --------------------------- | ----------------------------------------------------------------------------------------------- |
| `OUTPUT_DIR`      | `output`                    | Base output directory. Automatically creates `core/` and `derived/` subdirectories              |
| `TSV_CORE_DIR`    | `music_metadata`            | Directory containing core MusicBrainz TSV/TAR dumps (artists, recordings, releases, etc.)       |
| `TSV_DERIVED_DIR` | `music_derived_metadata`    | Directory containing derived MusicBrainz TSV/TAR dumps (labels, places, events, etc.)           |
| `CSV_CORE_DIR`    | `output/converted/core`     | Working directory where converted core CSV files are stored before preparation (auto-created)   |
| `CSV_DERIVED_DIR` | `output/converted/derived`  | Working directory where converted derived CSV files are stored before preparation (auto-created) |

### Sampling Options

| Variable                   | Default | Description                                                                                 |
| -------------------------- | ------- | ------------------------------------------------------------------------------------------- |
| `SAMPLE_PERCENT`           | `1.0`   | Percentage of data to process (0.0-100.0). Use lower values for testing                     |
| `SAMPLE_SEED`              | `42`    | Random seed for reproducible sampling. Ensures consistent results                           |
| `DEMO_SAMPLE_PERCENT`      | `0.1`   | Sampling percentage applied when running `build --demo`                                     |
| `DEMO_VECTOR_SAMPLE_PERCENT` | `0.1` | Sampling percentage applied to the vector build stage when running `build --demo`           |

### File Processing Options

| Variable             | Default | Description                                        |
| -------------------- | ------- | -------------------------------------------------- |
| `DELIMITER`          | `\t`    | Field delimiter in input TSV files (tab character) |
| `ENCODING`           | `utf-8` | Character encoding of input files                  |
| `SKIP_HEADERS`       | `false` | Skip generation of Neo4j header files              |
| `SKIP_LABELS`        | `false` | Skip processing of labeled node data               |
| `SKIP_RELATIONSHIPS` | `false` | Skip processing of relationship data               |

## Derived Data Processing Options

The pipeline supports processing additional MusicBrainz "derived" data to create a richer knowledge graph. These options control which additional entity types and relationships to include.

### Core Derived Entities

| Variable              | Default | Description                                                                              |
| --------------------- | ------- | ---------------------------------------------------------------------------------------- |
| `PROCESS_LABELS`      | `true`  | Record labels (Sony, Universal, etc.). Adds industry context and business relationships  |
| `PROCESS_MEDIUMS`     | `true`  | Physical media types (CD, Vinyl, Digital). Describes release formats and carriers        |
| `PROCESS_TRACKS`      | `true`  | Individual tracks within releases. Provides detailed track-level information             |
| `PROCESS_PLACES`      | `true`  | Recording locations, venues. Adds geographic and performance context                     |
| `PROCESS_EVENTS`      | `true`  | Concerts, festivals, events. Links artists to their performances and tours               |
| `PROCESS_GENRES`      | `true`  | Music genres. Enables genre-based queries and recommendations                            |
| `PROCESS_INSTRUMENTS` | `true`  | Musical instruments. Shows artist specializations and performance details                |
| `PROCESS_SERIES`      | `true`  | Album/Artist series. Groups related releases and connects collections                    |
| `PROCESS_URLS`        | `true`  | External links (Wikipedia, official sites). Provides additional resources and references |

### Metadata Enrichment

| Variable             | Default | Description                                                                    |
| -------------------- | ------- | ------------------------------------------------------------------------------ |
| `PROCESS_ALIASES`    | `true`  | Alternative names for entities. Improves search and handles name variations    |
| `PROCESS_TYPES`      | `true`  | Entity type classifications. Adds type information for better categorization   |
| `PROCESS_ATTRIBUTES` | `true`  | Additional properties and characteristics. Enriches entity metadata            |
| `PROCESS_CREDITS`    | `true`  | Artist credits and contributions. Shows detailed attribution and roles         |
| `PROCESS_LANGUAGES`  | `true`  | Work languages, release countries. Adds localization and regional information  |
| `PROCESS_PACKAGING`  | `true`  | Release packaging types. Describes physical release formats                    |
| `PROCESS_STATUSES`   | `true`  | Release statuses (Official, Bootleg). Indicates content quality and legitimacy |

### Extended Relationships

| Variable                               | Default | Description                                                                        |
| -------------------------------------- | ------- | ---------------------------------------------------------------------------------- |
| `PROCESS_EXTENDED_RELATIONSHIPS`       | `true`  | Process additional l\_\* relationship files. Adds complex inter-entity connections |
| `RELATIONSHIPS_TO_SKIP`                | -       | Comma-separated list of relationships to exclude. Useful for performance tuning    |
| `QUIET_MISSING_EXTENDED_RELATIONSHIPS` | `false` | Suppress warnings when optional l\_\* tables are absent in the provided dumps      |

**Example:** `RELATIONSHIPS_TO_SKIP=l_artist_event,l_genre_genre,l_url_work`

### Advanced Options

| Variable            | Default | Description                                                                               |
| ------------------- | ------- | ----------------------------------------------------------------------------------------- |
| `PROCESS_REDIRECTS` | `false` | GID redirects for data cleanup. Used for database maintenance and deduplication           |
| `PROCESS_ISNI_IPI`  | `false` | ISNI/IPI professional identifiers. For industry integration and professional verification |
| `PROCESS_ISRC_ISWC` | `false` | ISRC/ISWC recording/work codes. For rights management and content identification          |
| `PROCESS_CDTOC`     | `false` | CD Table of Contents. For CD identification and audio matching                            |

## Vector Build and Testing

| Variable                      | Default | Description                                                      |
| ----------------------------- | ------- | ---------------------------------------------------------------- |
| `VECTOR_BUILD_WORKERS`        | `12`    | Number of workers for vector building                            |
| `VECTOR_BUILD_SAMPLE_PERCENT` | `100.0` | Percentage of data to use when building the vector database      |
| `TEST_MODE`                   | `true`  | Enable test mode (uses `TEST_SAMPLE_PERCENT` instead of full set |
| `TEST_SAMPLE_PERCENT`         | `1.0`   | Sampling percentage for test mode                                |
| `VECTOR_LABELS`               | *(list)*| Comma-separated list of Neo4j labels to embed (defaults cover Artist, Recording, etc.) |

## Troubleshooting and Validation

After configuration, you can run a small validation build using:

```bash
uv run python main.py build --config .env
uv run python main.py build-vector
```

Use lower `SAMPLE_PERCENT` or enable `TEST_MODE` for faster iteration during development.
