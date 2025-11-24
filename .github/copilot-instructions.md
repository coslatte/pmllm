# Copilot Instructions for pmllm Project

## Project Overview
This is a Retrieval-Augmented Generation (RAG) system for music data using Neo4j (knowledge graph), Milvus (vector database), and LM Studio (LLM). It processes MusicBrainz data to provide recommendations and Q&A. Purpose: Help university students and professionals find courses, content, and connections using an LLM augmented with a knowledge graph. Primary users: university_students, professionals, platform_developers. Scope: course recommendation, professional connection suggestions, technical question answering. Success criteria: >=80% accuracy on curated Q&A test set, 50% reduction in average information-search time, recommendations are personalized and explainable.

## Architecture
- **CLI Entry**: `main.py` (Typer-based commands: build, build-vector, query)
- **Graph DB**: `db/neo4j/` - Neo4j handlers for importing/querying music relationships (logical brain for exact relations)
- **Vector Ops**: `db/vector/` - Embeddings via LM Studio API, Milvus storage, RAG pipeline (intuitive brain for semantic similarity)
- **Utils**: `utils/` - Data preparation, file management, constants
- **Config**: `.env` for all settings (URIs, models, sampling)

Data flow: TSV → CSV → Neo4j import → Vector embeddings → Milvus → RAG queries.

Milestones: Stage-1 (Data Prep: Completed), Stage-2 (DB Construction: Neo4j done, Vector pending), Stage-3 (RAG Consolidation: Pipeline and API).

The system uses a "two brains and one voice" metaphor: Neo4j as logical brain (exact facts), Milvus as intuitive brain (semantic meaning), Qwen 3 as voice (generation).

## Key Patterns
- **Environment**: Use `uv run python` for all executions (not plain `python`)
- **Sampling**: Deterministic via `elementId % MOD_BASE` (see `neo4j_handler.py`)
- **Multiprocessing**: 3-phase pipeline (import/transform/save) with queues (see `build_vector_db.py`)
- **Embeddings**: Batch API calls to LM Studio, fallback to sequential (see `embedder.py`); use `text-embedding-qwen3-embedding-0.6b` model
- **CLI**: Typer commands with `--help`, load dotenv early in `main.py`
- **Agent Guidelines**: When unsure, return 'I don't know' and suggest data collection. Include provenance/confidence in answers. Document changes in `docs/CHANGELOG.md` and `docs/CHANGELOG_es.md`. Use 'uv run python' for commands.

## Workflows
- **Setup**: `uv sync` to install deps, `docker-compose up -d` for Milvus
- **Import Data**: `uv run python main.py build --config .env` (TSV to Neo4j)
- **Build Vectors**: `uv run python main.py build-vector` (interactive prompts for CPU/sampling)
- **Query**: `uv run python main.py query "question"`
- **Debug**: Check `.env` for TEST_MODE (1% sampling), logs in terminal

## Conventions
- **Imports**: Standard libs first, then third-party, then local (PEP8)
- **Error Handling**: Try/except with logging, raise for critical errors
- **Async**: Multiprocessing over threading for CPU-bound tasks
- **Config**: All via env vars, no hardcoded values
- **Docs**: Update `docs/CHANGELOG.md` for changes
- **Contracts**: Content recommender (user_profile/history/query -> items/explanations/confidence), Connector (user_profile/goals -> candidates/reasons/confidence), QA responder (question -> answer/sources/confidence)

## Examples
- Add new label: Update `build_vector_db.py` labels list, ensure handler in `neo4j_handler.py`
- New embedding model: Modify `embedder.py` USE_LOCAL_EMBEDDING and model vars
- Custom sampling: Adjust `SAMPLE_PERCENT` in `.env` or code logic

Reference: `docs/plan/PLAN.md` for milestones, `docs/plan/general_plan.md` for architecture metaphor, `README.md` for high-level arch.