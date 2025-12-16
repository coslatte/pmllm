# Overview

The pmllm system uses environment variables for all configuration. Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
# Edit .env with your specific values
```

## Variable Categories

### Neo4j Connection Settings

| Variable               | Default                 | Description                                                                                                                                              |
| ---------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NEO4J_URI`            | `bolt://localhost:7687` | Neo4j connection URI. Use `bolt://` for secure connections or `neo4j://` for clustering                                                                  |
| `NEO4J_USER`           | `neo4j`                 | Neo4j database username                                                                                                                                  |
| `NEO4J_PASSWORD`       | `your_password_here`    | Neo4j database password. Required for authentication                                                                                                     |
| `NEO4J_DATABASE`       | `pmllmdb`               | Neo4j database name used by this project                                                                                                                 |
| `NEO4J_ALLOW_INSECURE` | `false`                 | Allow connections with default password. Only for development/testing                                                                                    |
| `NEO4J_DATA_DIR`       | -                       | Path to Neo4j data directory for local bulk imports. If NEO4J_BIN_PATH is set, this can be left empty. Example: ~/.Neo4jDesktop2/Data/dbmss/dbms-\*/data |
| `NEO4J_BIN_PATH`       | -                       | Path to Neo4j bin directory for bulk import tool. Example: ~/.Neo4jDesktop2/Data/dbmss/dbms-\*/bin                                                       |

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

### Chat & Preference Store

| Variable               | Default                                          | Description                                                                                         |
| ---------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| `CHAT_DB_USER`         | `pmllm`                                          | Database username injected into the `pmllm-user-db` Postgres container.                             |
| `CHAT_DB_PASSWORD`     | `pmllm`                                          | Database password (update for production).                                                          |
| `CHAT_DB_HOST`         | `pmllm-user-db`                                  | Hostname used by other containers to reach Postgres on the Docker network.                          |
| `CHAT_DB_PORT`         | `5432`                                           | Internal Postgres port (container).                                                                 |
| `CHAT_DB_EXTERNAL_PORT`| `5433`                                           | Optional port published to the host for local inspection via `psql` or GUI tools.                   |
| `CHAT_DB_NAME`         | `pmllm_chat`                                     | Database name that stores users, preferences, chats, and messages.                                  |
| `CHAT_DB_URL`          | `postgresql+psycopg2://pmllm:pmllm@pmllm-user-db:5432/pmllm_chat` | SQLAlchemy URL consumed by the FastAPI service. Leave blank to fall back to SQLite via `CHAT_DB_PATH`. |
| `CHAT_DB_PATH`         | `./storage/local_app.db`                         | Filesystem path for SQLite when Postgres is unavailable.                                            |
| `CHAT_SERVICE_URL`     | `http://localhost:8080`                          | Base URL for the FastAPI recommender service (used by the frontend or other clients).               |

### Model Gateway & API Settings

| Variable                         | Default                                        | Description                                                                                 |
| -------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `MODEL_GATEWAY_EMBEDDING_MODEL`  | `text-embedding-embeddinggemma-300m-qat`       | Gemma variant the gateway loads for `/v1/embeddings`.                                       |
| `MODEL_GATEWAY_LLM_MODEL`        | `gemma-3-1b-it-qat`                            | Gemma chat variant served from `/v1/chat/completions`.                                      |
| `MODEL_GATEWAY_DEVICE`           | `cpu`                                          | Device hint for the gateway container (e.g., `cuda`, `cpu`).                                 |
| `MODEL_GATEWAY_DTYPE`            | `float32`                                      | Torch dtype used when loading Gemma inside the gateway container.                           |
| `MODEL_GATEWAY_MAX_NEW_TOKENS`   | `512`                                          | Hard cap for tokens the gateway itself will generate per response.                           |
| `EMBEDDING_API_URL`              | `http://localhost:8081/v1/embeddings`          | Host-facing URL for requesting embeddings (gemma-embeddings container).                     |
| `EMBEDDING_MODEL`                | `text-embedding-embeddinggemma-300m-qat`       | Embedding model name echoed in API payloads.                                                |
| `EMBEDDING_API_TIMEOUT`          | `60`                                           | HTTP timeout (seconds) for embedding calls.                                                 |
| `LLM_API_URL`                    | `http://localhost:8082/v1/chat/completions`    | Host-facing URL for chat completions (gemma-chat container).                                |
| `LLM_MODEL`                      | `gemma-3-1b-it-qat`                            | Chat model identifier provided in API payloads.                                             |
| `LLM_MAX_NEW_TOKENS`             | `512`                                          | Default max tokens for generation.                                                          |
| `LLM_TEMPERATURE`                | `0.7`                                          | Default sampling temperature.                                                               |
| `LLM_API_TIMEOUT`                | `120`                                          | HTTP timeout (seconds) for chat completions.                                                |
| `MODEL_API_KEY`                  | _(blank)_                                      | Optional bearer token if you secure the gateway behind auth.                                |

> **Container reminder:** The Gemma embedding and chat models run in separate containers (`gemma-embeddings` and `gemma-chat`). Keep these services running whenever you build vectors or answer queries. Override the `_API_URL` values with `http://gemma-embeddings:8080/...` or `http://gemma-chat:8080/...` when calling from another container on the same Docker network.

## Build Process Configuration

### Input/Output Directories

| Variable          | Default                    | Description                                                                                      |
| ----------------- | -------------------------- | ------------------------------------------------------------------------------------------------ |
| `OUTPUT_DIR`      | `output`                   | Base output directory. Automatically creates `core/` and `derived/` subdirectories               |
| `TSV_CORE_DIR`    | `music_metadata`           | Directory containing core MusicBrainz TSV/TAR dumps (artists, recordings, releases, etc.)        |
| `TSV_DERIVED_DIR` | `music_derived_metadata`   | Directory containing derived MusicBrainz TSV/TAR dumps (labels, places, events, etc.)            |
| `CSV_CORE_DIR`    | `output/converted/core`    | Working directory where converted core CSV files are stored before preparation (auto-created)    |
| `CSV_DERIVED_DIR` | `output/converted/derived` | Working directory where converted derived CSV files are stored before preparation (auto-created) |

### Sampling Options

| Variable                     | Default | Description                                                                       |
| ---------------------------- | ------- | --------------------------------------------------------------------------------- |
| `SAMPLE_PERCENT`             | `100.0` | Percentage of data to process (0.0-100.0). Use lower values for testing           |
| `SAMPLE_SEED`                | `123`   | Random seed for reproducible sampling. Ensures consistent results                 |
| `DEMO_MODE`                  | `true`  | Enable demo mode (overrides sampling settings for quick testing)                  |
| `DEMO_SAMPLE_PERCENT`        | `0.1`   | Sampling percentage applied when running `build --demo`                           |
| `DEMO_VECTOR_SAMPLE_PERCENT` | `0.1`   | Sampling percentage applied to the vector build stage when running `build --demo` |

### File Processing Options

| Variable             | Default | Description                                        |
| -------------------- | ------- | -------------------------------------------------- |
| `DELIMITER`          | `\t`    | Field delimiter in input TSV files (tab character). Must be a single character; use actual tab in .env if needed |
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

| Variable                      | Default  | Description                                                                            |
| ----------------------------- | -------- | -------------------------------------------------------------------------------------- |
| `VECTOR_BUILD_WORKERS`        | `4`      | Number of workers for vector building                                                  |
| `VECTOR_BUILD_SAMPLE_PERCENT` | `1.0`    | Percentage of data to use when building the vector database                            |
| `TEST_MODE`                   | `true`   | Enable test mode (uses `TEST_SAMPLE_PERCENT` instead of full set)                      |
| `TEST_SAMPLE_PERCENT`         | `1.0`    | Sampling percentage for test mode                                                      |
| `VECTOR_LABELS`               | _(list)_ | Comma-separated list of Neo4j labels to embed (defaults cover Artist, Recording, etc.) |

## Troubleshooting and Validation

After configuration, you can run a small validation build using:

```bash
uv run python main.py build --config .env
uv run python main.py build-vector
```

Use lower `SAMPLE_PERCENT` or enable `TEST_MODE` for faster iteration during development.
