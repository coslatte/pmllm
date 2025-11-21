# Knowledge-Graph + Retrieval-Augmented Generation (RAG) with Qwen 3 — Music Recommendation & Relationship Tool

This repository contains a project plan and supporting material for building a Knowledge-Graph-augmented Retrieval-Augmented Generation (RAG) system that uses the Qwen 3 family (e.g., `qwen/qwen3-1.7b`) as the LLM for generation. We no longer pursue model fine-tuning. Instead, the system uses embeddings + a vector store for retrieval and Qwen 3 for high-quality, instruction-following generation over retrieved context. The goal remains: explainable recommendations, relationship discovery across music-related subjects (courses, genres, artists, topics), and contextual question answering for students, educators, and music professionals.

## Purpose

- Provide personalized recommendations (courses, pieces, playlists, resources) in music education and practice.
- Reveal relationships and paths between related music subjects (e.g., harmony -> counterpoint -> orchestration), genres, or artists using an explicit knowledge graph.
- Support technical and domain-level Q&A with cited sources and confidence scoring.

## High-level architecture (RAG + KG)

1. Document & KG ingestion: convert documents and KG nodes into embeddings and index them in a vector store (and keep KG for structured queries).
2. Embeddings & Vector Store: an embeddings model (cloud or open-source) creates vectors for documents; a vector DB provides nearest-neighbor retrieval. For this project we will use Milvus as the production vector database (development may use local FAISS for quicker iteration).
3. Retriever: given a user query, retrieve relevant passages/documents and KG facts from the vector store and KG.
4. Generator (Qwen 3): compose a prompt that includes retrieved context and use Qwen 3 (e.g., `qwen/qwen3-1.7b`) to generate answers, recommendations, and explanations. No fine-tuning required — rely on prompt engineering and retrieval context.
5. Orchestration & business logic: combine KG reasoning, retrieved passages, prompt templates, and post-processing (citations, confidence scoring, ranking) to produce final outputs.
6. API & UI: REST endpoints (e.g., `/recommend`, `/connect`, `/ask`) and simple UI or CLI to query the system.
7. Evaluator & Monitoring: automated tests and metrics for accuracy, retrieval quality (recall/precision), latency, and user satisfaction.

See `plan/PLAN.md` for the structured, agent-friendly plan and task contracts.

## Data sources (examples)

- University/academy course catalogs
- Music theory textbooks and lecture notes
- Artist/genre taxonomies and discographies
- Curated Q&A pairs and annotated datasets for validation and retrieval testing
- User profiles and interaction logs (privacy-preserving, anonymized)
- Fragmented MusicBrainz dataset (extracted portion): a dataset we downloaded from a MusicBrainz server snapshot; the original source uses PostgreSQL for tabular music metadata and Neo4j for relations. We'll extract documents and KG nodes from this fragmented dump and ingest them into the vector store (Milvus) and our KG layer (Neo4j or a compatible graph store).

### MusicBrainz Graph Architecture (Verified)

The MusicBrainz-to-Neo4j pipeline creates a comprehensive knowledge graph with:

**Core Node Types (7):**

- **Artist** (15 fields): Core entity with biographical data
- **Recording** (7 fields): Individual music tracks
- **Release** (7 fields): Album/product releases
- **Work** (6 fields): Musical compositions
- **Area** (5 fields): Geographic locations
- **ReleaseGroup** (7 fields): Logical release groupings
- **Tag** (3 fields): Genre and categorization labels

**Derived Node Types (9 - configurable):**

- **Label** (15 fields): Record labels (Sony, Universal, etc.)
- **Medium** (6 fields): Physical media types (CD, Vinyl, Digital)
- **Track** (9 fields): Individual tracks within releases
- **Place** (8 fields): Recording locations, venues
- **Event** (12 fields): Concerts, festivals, events
- **Genre** (5 fields): Music genres
- **Instrument** (6 fields): Musical instruments
- **Series** (7 fields): Album/artist series
- **Url** (2 fields): External links (Wikipedia, official sites)

**Relationship Types (25+):**

*Core relationships:*

- Artist → Recording (`PERFORMED_ON`): Artist credits on recordings
- Artist → Release (`RELEASED`): Artist participation in releases
- Recording → Work (`BELONGS_TO`): Composition relationships
- Release → ReleaseGroup (`BELONGS_TO`): Release hierarchies
- Artist → Area (`FROM_AREA`): Geographic origins
- Release → Area (`RELEASED_IN`): Release locations
- Recording → Tag (`HAS_TAG`): Genre classification
- Artist → Tag (`HAS_TAG`): Artist categorization
- Release → Tag (`HAS_TAG`): Release tagging

*Extended relationships (derived data):*

- Label → Release (`PUBLISHED`): Label publishing relationships
- Label → Recording (`DISTRIBUTED`): Label distribution relationships
- Artist → Place (`PERFORMED_AT`): Performance venues
- Release → Place (`RECORDED_AT`): Recording locations
- Recording → Place (`RECORDED_AT`): Recording studios
- Artist → Event (`PERFORMED_AT`): Concert appearances
- Release → Event (`PROMOTED_AT`): Event promotions
- Recording → Event (`FEATURED_AT`): Event features
- Artist → Genre (`BELONGS_TO`): Genre associations
- Release → Genre (`BELONGS_TO`): Release genres
- Recording → Genre (`BELONGS_TO`): Recording genres
- Artist → Instrument (`PLAYS`): Instrument specializations
- Recording → Url (`AVAILABLE_AT`): Streaming/download links
- Release → Url (`AVAILABLE_AT`): Release links
- Artist → Url (`OFFICIAL_SITE`): Artist websites
- Work → Url (`SCORE_AT`): Sheet music links
- Label → Url (`OFFICIAL_SITE`): Label websites

**Quality Assurance:**

- ✅ 100% schema integrity validated
- ✅ All relationships logically connected
- ✅ Sampling-compatible for large datasets
- ✅ Excludes overly specific data points
- ✅ Optimized for music recommendation use cases

### Derived Data Configuration

The pipeline now supports processing additional MusicBrainz "derived" data files that significantly enrich the knowledge graph. Configure which derived data to include in your `.env` file:

```bash
# Core derived entities (recommended: true for richer metadata)
PROCESS_LABELS=true          # Record labels (Sony, Universal, etc.)
PROCESS_MEDIUMS=true         # Physical media types (CD, Vinyl, Digital)
PROCESS_TRACKS=true          # Individual tracks within releases
PROCESS_PLACES=true          # Recording locations, venues
PROCESS_EVENTS=true          # Concerts, festivals, events
PROCESS_GENRES=true          # Music genres
PROCESS_INSTRUMENTS=true     # Musical instruments
PROCESS_SERIES=true          # Album/Artist series
PROCESS_URLS=true            # External links (Wikipedia, official sites)

# Extended relationships
PROCESS_EXTENDED_RELATIONSHIPS=true  # Additional l_* relationship files
```

**Benefits of derived data:**

- **Enhanced recommendations**: More connection paths between artists, works, and locations
- **Geographic insights**: Recording studios, performance venues, artist origins
- **Industry context**: Record labels, release formats, distribution networks
- **Rich metadata**: Genres, instruments, events, and external references
- **Better search**: More entry points for discovering music relationships

Notes on the MusicBrainz fragment:

- The fragment contains artist, release, recording, and relationship data exported from a MusicBrainz server. The upstream storage format for that data is PostgreSQL (core tables) and Neo4j for richer relation exports in some pipelines.
- Our ingestion pipeline will include scripts to read the PostgreSQL dump and Neo4j exports, convert relevant rows/graphs to text passages and KG nodes, create embeddings, and upsert them into Milvus and the KG store.
- Do not commit database dumps or credentials to the repo. Document connection and import steps in `scripts/README.md` or `docs/DEPLOY.md` and load secrets via environment variables or a secure vault.

## Current Implementation

### Implemented Components

- `cli.py` / `main.py` — Command-line interface for dataset conversion, Neo4j import, and full build automation
- `db/vector/` — Vector database integration with Milvus
  - `milvus_store.py` — Milvus connection and collection management
  - `vector_query.py` — Vector similarity search
  - `rag_pipeline.py` — RAG orchestration with Qwen 3 LLM
  - `build_vector_db.py` — Populate vector DB from Neo4j nodes
- `db/neo4j/` — Neo4j graph database integration
  - `neo4j_handler.py` — Query and retrieve nodes from Neo4j
  - `neo4j_importer.py` — Bulk import data into Neo4j
- `utils/files_manager/` — Data processing utilities
  - `converter.py` — TSV to CSV conversion
  - `reader.py` — File reading and validation
  - `csv_helper.py` — MusicBrainz data preparation for Neo4j
- `pyproject.toml` / `requirements.txt` — Python dependencies
- `docker-compose.yml` — Milvus service configuration

### Planned Components

- REST API server exposing endpoints (`/recommend`, `/connect`, `/ask`)
- Evaluation and monitoring code (retrieval and generation metrics)
- Additional data processors for specific use cases

## Documentation

- `docs/CLI_USAGE.md` — Comprehensive CLI usage guide with examples, sampling strategies, and validation features
- `docs/CHANGELOG.md` — Log of all changes made to the project, especially by agents
- `ENVIRONMENT.md` — Detailed environment variables configuration guide
- `plan/PLAN.md` — Structured project plan
- `plan/original_plan.md` — Original plan with annotations

Additional notes:

- Vector DB: Milvus is our chosen production vector store. We'll use Milvus's Python client for ingestion and retrieval; configuration (host/port/credentials) will be provided through env vars.
- KG & relations: Neo4j will be the primary graph database for storing relations and KG facts derived from the MusicBrainz fragment. We will keep KG queries and vector retrievals linked via stable identifiers so we can surface structured relations alongside retrieved passages.

## Agent usage notes

- Agents should parse the YAML metadata block in `plan/PLAN.md` first to discover priorities, milestones, and task contracts.
- Use the `agent_instructions` section in `plan/PLAN.md` for expected I/O formats (JSON task inputs and JSON outputs with `result`, `explanation`, `confidence`, and `sources`).
- Always include data provenance and a confidence score with answers. When answering, include which retrieved passages or KG facts were used and link to their identifiers.

Note: the project now uses a RAG approach with Qwen 3. Do not add or expect fine-tuning scripts or fine-tuned model artifacts in the repo unless a future decision reintroduces fine-tuning.

## Development / Installation

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for Milvus vector database)
- Neo4j (via Neo4j Desktop or Docker)
- Java (for Neo4j bulk import)

### Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone https://github.com/coslatte/pmllm.git
   cd pmllm
   ```

2. **Create and activate a Python virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   # Or using the project file:
   pip install -e .
   ```

4. **Set up environment variables:**
   Create a `.env` file or export these variables:

   ```bash
   # Neo4j connection
   export NEO4J_URI="bolt://localhost:7687"
   export NEO4J_USER="neo4j"
   export NEO4J_PASSWORD="your_password"

   # Milvus connection (optional, defaults shown)
   export MILVUS_HOST="127.0.0.1"
   export MILVUS_PORT="19530"

   # LLM API endpoint (for Qwen via LM Studio)
   export QWEN_GENERATE_URL="http://localhost:1234/v1/chat/completions"
   export QWEN_GENERATE_MODEL="qwen-1.7b"

   # Embedding model (optional)
   export EMBEDDING_MODEL_PATH="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
   ```

   For a complete list of environment variables and their descriptions, see `ENVIRONMENT.md`.

5. **Start Milvus services:**

   ```bash
   docker-compose up -d
   ```

6. **Run the CLI to verify installation:**

   ```bash
   python main.py --help
   # Or directly:
   python cli.py --help
   ```

### Usage Examples

**Full automated build (recommended):**

```bash
# Configure settings in .env file
cp .env.example .env
# Edit .env with your paths and settings

# Run complete pipeline: convert TSV → prepare data → import to Neo4j
python cli.py build
```

**Individual steps:**

**Convert TSV files to CSV:**

```bash
python cli.py convert /path/to/tsv/files -o output_csv
```

**Prepare MusicBrainz data for Neo4j:**

```bash
python cli.py prepare-neo4j \
  --mbdump mbdump \
  --headers-dir neo4j_headers \
  --labeled-dir labeled \
  --relationships-dir relationships \
  --sample-percent 10.0  # Use 10% sample for testing
```

**Import data into Neo4j:**

```bash
python cli.py import-neo4j \
  --headers-dir neo4j_headers \
  --labeled-dir labeled \
  --relationships-dir relationships \
  --db-name musicbrainz.db \
  --verify
```

See `docs/CLI_USAGE.md` for comprehensive CLI documentation including sampling modes, validation features, and advanced usage examples.
