# PMLLM - Music Knowledge Graph RAG System

## Complete Project Summary

This document provides a comprehensive overview of the PMLLM (Personalized Music Language Learning Model) system, consolidating all architectural decisions, components, and usage patterns into a single reference.

---

## 1. Project Overview

### Purpose

PMLLM is a Retrieval-Augmented Generation (RAG) system for music data that combines:

- **Knowledge Graph** (Neo4j) for structured relationships
- **Vector Database** (Milvus) for semantic similarity
- **Large Language Model** (Gemma 3) for natural language generation

### Target Users

- University students seeking music education resources
- Professionals exploring music industry connections
- Platform developers building recommendation features

### Success Criteria

- ≥80% accuracy on curated Q&A test set
- 50% reduction in average information-search time
- Personalized and explainable recommendations

---

## 2. Architecture

### "Two Brains and One Voice" Metaphor

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RAG ORCHESTRATOR                                │
│                    (rag_pipeline.py)                                │
└─────────────────────────────────────────────────────────────────────┘
           │                                         │
           ▼                                         ▼
┌─────────────────────┐                 ┌─────────────────────┐
│   LOGICAL BRAIN     │                 │  INTUITIVE BRAIN    │
│      (Neo4j)        │                 │     (Milvus)        │
│                     │                 │                     │
│ • Exact facts       │                 │ • Semantic meaning  │
│ • Relationships     │                 │ • Vector embeddings │
│ • Graph traversal   │                 │ • Similarity search │
└─────────────────────┘                 └─────────────────────┘
           │                                         │
           └──────────────────┬──────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         VOICE                                        │
│                   (Gemma 3 LLM)                                     │
│                                                                      │
│    • Natural language generation                                     │
│    • Context-aware responses                                         │
│    • Explainable recommendations                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      USER RESPONSE                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Container Topology

| Container               | Port  | Purpose                                        |
|-------------------------|-------|------------------------------------------------|
| `milvus-standalone`     | 19530 | Vector database for embeddings                 |
| `milvus-etcd`           | -     | Milvus metadata coordination                   |
| `milvus-minio`          | 19000 | Object storage for Milvus                      |
| `gemma-embeddings`      | 8081  | Embedding generation (llama.cpp server)        |
| `gemma-chat`            | 8082  | Chat completions (llama.cpp server)            |
| `pmllm-user-db`         | 5433  | PostgreSQL for user data/chats                 |
| `pmllm-recommender-api` | 8080  | FastAPI backend for frontend                   |

---

## 3. Data Pipeline

### Data Flow

```
MusicBrainz TSV/TAR Dumps
         │
         ▼ (convert command)
    CSV Working Sets
         │
         ▼ (prepare-neo4j command)
    Neo4j Headers + Labeled Data + Relationships
         │
         ▼ (import-neo4j command)
    Neo4j Graph Database
         │
         ▼ (build-vector command)
    Milvus Vector Database
         │
         ▼ (query command / API)
    RAG Responses
```

### Entity Types

**Core Nodes (7):**
- Artist (15 fields)
- Recording (7 fields)
- Release (7 fields)
- Work (6 fields)
- Area (5 fields)
- ReleaseGroup (7 fields)
- Tag (3 fields)

**Derived Nodes (9, configurable):**
- Label, Medium, Track, Place, Event, Genre, Instrument, Series, Url

**Relationships (25+):**
- PERFORMED_ON, RELEASED, BELONGS_TO, FROM_AREA, HAS_TAG, PUBLISHED, PLAYS, etc.

---

## 4. Project Structure

```
pmllm/
├── main.py                 # CLI entry point (Typer-based)
├── docker-compose.yml      # Container orchestration
├── .env                    # Environment configuration
├── pyproject.toml          # Python dependencies
│
├── db/
│   ├── neo4j/
│   │   ├── neo4j_handler.py    # Neo4j query operations
│   │   └── neo4j_importer.py   # Bulk import logic
│   └── vector/
│       ├── build_vector_db.py  # Populate Milvus from Neo4j
│       ├── milvus_store.py     # Milvus connection
│       ├── rag_pipeline.py     # RAG orchestration
│       ├── vector_query.py     # Vector search
│       └── helper/
│           ├── embedder.py     # Embedding API client
│           ├── llm_handler.py  # LLM API client
│           └── text_builder.py # Text generation for nodes
│
├── server/
│   ├── main.py                 # FastAPI application
│   ├── database.py             # SQLAlchemy models
│   ├── query_engine.py         # RAG query endpoint
│   ├── recommendation_engine.py # Recommendation logic
│   └── milvus_handler.py       # User profile vectors
│
├── model_gateway/
│   ├── app.py                  # FastAPI embedding/LLM server
│   ├── Dockerfile              # Container build
│   └── requirements.txt        # Gateway dependencies
│
├── utils/
│   ├── cli_helpers.py          # CLI utilities
│   ├── constants.py            # Shared constants
│   ├── data_builder.py         # Data preparation
│   ├── files_manager/
│   │   ├── converter.py        # TSV to CSV conversion
│   │   ├── csv_helper.py       # Neo4j CSV preparation
│   │   └── reader.py           # File reading utilities
│   └── helpers/
│       ├── convert_handler.py
│       ├── import_handler.py
│       └── prepare_handler.py
│
├── docs/
│   ├── PROJECT_SUMMARY.md      # This file
│   ├── API_DOCUMENTATION.md    # REST API reference
│   ├── CLI_USAGE.md            # CLI command guide
│   ├── ENVIRONMENT.md          # Environment variables
│   ├── CHANGELOG.md            # Version history
│   ├── DATASET.md              # Data documentation
│   ├── DISTRIBUCION_DATOS.md   # Data architecture (ES)
│   ├── RECOMMENDATION_SYSTEM.md # Recommendation contracts
│   ├── es_ES/                  # Spanish translations
│   └── plan/                   # Project planning docs
│
└── data/
    ├── milvus/                 # Milvus data volumes
    ├── neo4j/                  # Neo4j data volumes
    └── postgres/               # PostgreSQL data volumes
```

---

## 5. CLI Commands

### Primary Commands

| Command           | Description                                                    |
|-------------------|----------------------------------------------------------------|
| `build`           | Full pipeline: convert → prepare → import → vector build       |
| `build --demo`    | Demo build with sampling overrides                             |
| `start`           | Start Docker services + FastAPI server                         |
| `query`           | Query the RAG system                                           |

### Build Profiles

| Profile           | Description                                                    |
|-------------------|----------------------------------------------------------------|
| `full`            | Complete pipeline (convert → prepare → import → embeddings)    |
| `demo`            | Full with demo sampling overrides                              |
| `neo4j-only`      | Skip to Neo4j bulk import                                      |
| `embeddings-only` | Skip to vector database build                                  |
| `conversion-only` | Only convert TAR/TSV to CSV                                    |

### Usage Examples

```bash
# Demo build (minimal dataset)
uv run python main.py build --demo

# Full production build
uv run python main.py build --config .env

# Embeddings only (Neo4j already populated)
uv run python main.py build --profile embeddings-only

# Query the system
uv run python main.py query "What artists are similar to Queen?"

# Start all services
uv run python main.py start
```

---

## 6. Key Environment Variables

### Database Connections

| Variable             | Default                      | Description                    |
|----------------------|------------------------------|--------------------------------|
| `NEO4J_URI`          | `bolt://localhost:7687`      | Neo4j Bolt connection          |
| `NEO4J_USER`         | `neo4j`                      | Neo4j username                 |
| `NEO4J_PASSWORD`     | -                            | Neo4j password                 |
| `MILVUS_HOST`        | `127.0.0.1`                  | Milvus server host             |
| `MILVUS_PORT`        | `19530`                      | Milvus server port             |

### Model Gateway

| Variable              | Default                                    | Description                    |
|-----------------------|--------------------------------------------|--------------------------------|
| `EMBEDDING_API_URL`   | `http://localhost:8082/v1/embeddings`      | Embedding endpoint             |
| `EMBEDDING_MODEL`     | `text-embedding-embeddinggemma-300m-qat`   | Embedding model name           |
| `LLM_API_URL`         | `http://localhost:8082/v1/chat/completions`| Chat completions endpoint      |
| `LLM_MODEL`           | `gemma-3-1b-it-qat`                        | LLM model name                 |

### Sampling Controls

| Variable                    | Default | Description                              |
|-----------------------------|---------|------------------------------------------|
| `SAMPLE_PERCENT`            | `0.08`  | Data sampling percentage                 |
| `DEMO_MODE`                 | `true`  | Enable demo mode                         |
| `DEMO_VECTOR_SAMPLE_PERCENT`| `100`   | Vector build sampling in demo mode       |
| `TEST_MODE`                 | `false` | Enable test mode (additional sampling)   |
| `VECTOR_BUILD_SAMPLE_PERCENT`| `100`  | Vector build sampling percentage         |

---

## 7. API Endpoints

### User Management

| Method | Endpoint       | Description                    |
|--------|----------------|--------------------------------|
| POST   | `/users`       | Create a new user              |
| GET    | `/users/{id}`  | Get user by ID                 |

### Preferences

| Method | Endpoint       | Description                    |
|--------|----------------|--------------------------------|
| POST   | `/preferences` | Update user preferences        |
| GET    | `/preferences` | Get user preferences           |

### Chat

| Method | Endpoint                  | Description                    |
|--------|---------------------------|--------------------------------|
| POST   | `/chat`                   | Create new chat session        |
| POST   | `/message`                | Send message in chat           |
| GET    | `/chat/{id}/messages`     | Get chat history               |

### Query & Recommendations

| Method | Endpoint                     | Description                    |
|--------|------------------------------|--------------------------------|
| POST   | `/query`                     | RAG query with context         |
| POST   | `/recommendations`           | Get personalized recommendations|
| POST   | `/recommendations/albums`    | Get album recommendations      |

---

## 8. Recommendation System

### Output Contract

```json
{
  "recommendations": [
    {
      "type": "course | content | connection | album_plan",
      "title": "Short descriptive name",
      "description": "One-sentence summary",
      "explanation": "Traceable reasoning citing graph nodes or vector hits",
      "confidence": 0.0-1.0,
      "sources": ["neo4j:Artist(Queen)", "milvus:vector_id_123"],
      "suggested_actions": ["Listen on platform", "Connect with curator"]
    }
  ],
  "general_summary": "Overview of recommendations"
}
```

### Quality Criteria

- Return 5-10 entries when data suffices
- Prefer confidence ≥ 0.7
- Always cite sources (Neo4j nodes or Milvus vectors)
- Handle ambiguity by asking for clarification

---

## 9. Development Workflow

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Neo4j Desktop or Server
- Java (for Neo4j bulk import)

### Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/coslatte/pmllm.git
cd pmllm

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your paths and settings

# 4. Start containers
docker compose up -d

# 5. Run demo build
uv run python main.py build --demo

# 6. Query the system
uv run python main.py query "Recommend albums similar to Queen"
```

### Container Management

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f gemma-embeddings

# Check container status
docker ps

# Stop services
docker compose down
```

---

## 10. Current Status (December 2025)

### Completed (Stage 1 & 2)

- ✅ Data preparation pipeline (TSV → CSV → Neo4j)
- ✅ Neo4j graph database with MusicBrainz data
- ✅ Milvus vector database integration
- ✅ Embedding generation via llama.cpp containers
- ✅ RAG pipeline with hybrid retrieval
- ✅ CLI with build profiles and query support
- ✅ FastAPI server with user/chat management
- ✅ Docker Compose orchestration

### In Progress (Stage 3)

- 🔄 Frontend React application
- 🔄 Advanced recommendation algorithms
- 🔄 Evaluation and testing framework

### Planned

- 📋 Production deployment configuration
- 📋 Monitoring and logging infrastructure
- 📋 Extended evaluation metrics

---

## 11. Related Documentation

| Document                      | Description                                    |
|-------------------------------|------------------------------------------------|
| `docs/CLI_USAGE.md`           | Detailed CLI command reference                 |
| `docs/API_DOCUMENTATION.md`   | REST API specification                         |
| `docs/ENVIRONMENT.md`         | Environment variable reference                 |
| `docs/RECOMMENDATION_SYSTEM.md`| Recommendation contracts and prompts          |
| `docs/DATASET.md`             | MusicBrainz data documentation                 |
| `docs/DISTRIBUCION_DATOS.md`  | Data architecture (Spanish)                    |
| `docs/CHANGELOG.md`           | Version history and changes                    |
| `docs/plan/PLAN.md`           | Project milestones and tasks                   |
| `docs/plan/general_plan.md`   | Architecture overview (Spanish)                |

---

## 12. Contacts & Resources

- **Repository**: https://github.com/coslatte/pmllm
- **MusicBrainz**: https://musicbrainz.org
- **Milvus Docs**: https://milvus.io/docs
- **Neo4j Docs**: https://neo4j.com/docs
- **Gemma Models**: https://ai.google.dev/gemma

---

*Last updated: December 14, 2025*
