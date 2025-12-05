# Change Log

This file documents all changes made to the project, especially those implemented by agents.

> Note: The project standardizes on Gemma family models served from local containers via
> the `pmllm-model-gateway` (exposing an OpenAI-compatible `/v1` API). Older references
> to "LM Studio" or "Qwen 3" in historical entries are outdated and have been superseded
> by the current approach: containerized local models (Gemma) exposing embedding and
> generation endpoints. Configuration variables such as `EMBEDDING_API_URL`,
> `LLM_API_URL`, `EMBEDDING_MODEL` and `LLM_MODEL` control the gateway behavior.

## 2025-12-05

- **HTTP Health Checks**: Relaxed the `start` command's HTTP ping so endpoints that respond with client errors (e.g., 404/405 when accessed via GET) are still treated as reachable. This prevents false negatives when verifying the Gemma embedding/chat services that only expose POST routes.
- **Runtime DB Override**: `server/database.py` now honors `CHAT_DB_RUNTIME_URL`, letting local CLI runs target the Postgres port exposed on the host (`127.0.0.1:5433`) without touching the container-friendly `CHAT_DB_URL` value.
- **Album Recommendations API**: Added `POST /recommendations/albums`, which queries Neo4j for releases connected to the user's preferred genres (and filters out disliked ones). It returns structured album suggestions with the graph relationships that justify each pick so the frontend can render a "genres you might love" shelf.

## 2025-12-04

- **Containerized Runtime Fixes**: Updated `docker-compose.yml` so the Postgres service mounts `./data/postgres` at `/var/lib/postgresql`, matching the 18+ layout and preventing the health-check restart loop. Existing data was snapshotted under `data/postgres_legacy_*` before recreating the fresh volume.
- **Gateway Endpoint Alignment**: Pointed `.env` `EMBEDDING_API_URL`/`EMBEDDING_URL` to `http://127.0.0.1:8081/v1/embeddings` and `LLM_API_URL` to `http://127.0.0.1:8082/v1/chat/completions`, so local CLI tooling and the RAG pipeline hit the Gemma containers that run inside `docker compose` instead of the old LM Studio port (1234).
- **Delimiter Normalization**: Added a `_normalize_delimiter` helper in `main.py` and wired it into `build-data`, `prepare-neo4j`, `prepare-desktop`, `import-neo4j`, and the build-plan execution path. CLI options and `.env` values like `\t` now resolve to a true tab character, preventing Python's "delimiter must be a 1-character string" crashes and keeping conversions/imports consistent across commands.
- **Neo4j Dataset Refresh**: Rebuilt the Neo4j-ready CSVs with the corrected delimiter handling and reran the bulk import, yielding ~515k sampled nodes and 2.4k relationships from the latest 1% dataset slice.
- **Layered Test Sampling**: `db/vector/build_vector_db.py` now honors `TEST_SAMPLE_PERCENT`, so enabling `TEST_MODE` lets us take a percentage of the already-downsampled graph (e.g., 10% of the 1% Neo4j slice). `.env` defaults now set `SAMPLE_PERCENT=1` and `TEST_SAMPLE_PERCENT=10` to keep demo/test runs lightweight by default.
- **Frontend Query Bridge**: Introduced `server/query_engine.py` plus a `POST /query` FastAPI endpoint that funnels frontend prompts through the RAG pipeline, persists chat history (when `chat_id` is provided), detects tag/genre intents such as “tags de todos los artistas que son Jesus,” runs targeted Neo4j lookups for matching artists, and returns both the LLM answer and structured matches for UI rendering. Documented the new contract in `docs/API_DOCUMENTATION.md` and `docs/es_ES/API_DOCUMENTATION.md`.
- **Debuggable Queries + Clean Shutdown**: Added an optional `debug` flag to `/query` (and the CLI) that surfaces the exact prompt, context chunks, vector hits, and Neo4j relations used during retrieval. Implemented `ContextBundle` telemetry, richer responses, and CLI printing. Also registered an `atexit` hook plus simplified Cypher fallbacks so Neo4j stops warning about missing `title` properties and the Bolt driver closes cleanly after CLI runs.

## 2025-12-03

- **Build Command Profiles**: Introduced selectable build profiles in `main.py` backed by a `BuildProfile` enum and `--profile/-p` option. The CLI now offers interactive profile selection (falling back to `full` in non-interactive shells) with dedicated flows for demo, Neo4j-import-only, embeddings-only, and conversion-only scenarios. `_execute_full_build` skips steps according to the chosen plan, adds stronger directory validation when reusing artifacts, and improves readiness prompts.
- **Documentation Updates**: Documented the new profiles/flag in `docs/CLI_USAGE.md` and `docs/es_ES/CLI_USAGE.md`, including brief descriptions of each profile.
- **Demo Sampling Floor**: Increased `.env` demo/test sampling percentages to 1% so `build --demo` generates enough rows for Neo4j and Milvus without manual overrides.
- **Empty Import Guard**: Added a labeled-CSV sanity check in `main.py` that aborts the Neo4j bulk import when the sampled dataset lacks core nodes, preventing silent zero-node graphs.
- **Conversion Log Paths**: Trimmed the TSV→CSV conversion logs in `utils/files_manager/converter.py` so both source and destination paths show only the final directories (prefixed with `...\`) instead of full absolute paths.

## 2025-12-02

- **Stack Bootstrap CLI**: Added a `start` subcommand to `main.py` that optionally runs `docker compose up -d`, performs readiness checks for Neo4j, Milvus, and the model gateway endpoints, and launches the FastAPI server with `uvicorn`. The command supports `--skip-compose`, `--no-server`, custom host/port, and `--reload` for development.
- **Documentation Updates**: Extended `docs/CLI_USAGE.md` (EN/ES) with quick-start guidance, option tables, and troubleshooting notes for the new `start` command so developers know how to bring the full stack online.
- **Containerized User DB & Model Gateway**: Added a Postgres 15 service (`pmllm-user-db`) plus new environment variables so the FastAPI server persists users/chats via SQLAlchemy instead of local SQLite. Created a self-contained `model_gateway` FastAPI project (Dockerfile + code) that hosts Gemma embeddings and chat completions with an OpenAI-compatible `/v1` API, wired health checks/volumes in `docker-compose.yml`, refreshed `.env.example`, README, and ENVIRONMENT docs (EN/ES), and added `psycopg2-binary` to the Python dependencies.

## 2025-12-01

- **Model Gateway & Container Stack**: Added the `model_gateway` FastAPI service (embeddings + chat completions) with Dockerfile, requirements, and compose wiring, plus the `pmllm-recommender-api` container backed by a configurable SQLite path. Updated `.env` / `.env.example`, docker-compose, CLI helpers, tests, and all docs (README, ENVIRONMENT, CLI_USAGE, DISTRIBUCION_DATOS, plan files, Copilot instructions, EN/ES variants) to describe the three-container topology (Milvus, model gateway, chat DB) and the Gemma defaults.
- **Local LLM Integration**: Implemented direct interaction with LLM models using Transformers library instead of LM Studio API. Added `db/vector/helper/llm_handler.py` for local model loading and generation. Updated `rag_pipeline.py` to use local LLM. Added new environment variables: `USE_LOCAL_LLM`, `LLM_MODEL_NAME`, `LLM_DEVICE`, `LLM_MAX_NEW_TOKENS`, `LLM_TEMPERATURE`. Updated dependencies in `pyproject.toml` to include `transformers`, `torch`, `accelerate`.
- **Neo4j Desktop Bundle CLI**: Added the `prepare-desktop` command to `main.py`, plus `utils/helpers/desktop_bundle_handler.py`, so we can merge headers and data into Neo4j Desktop–ready CSVs (nodes + relationships) under `output/neo4j_desktop` for simple drag-and-drop imports.
- **Data Distribution Documentation**: Added `docs/DISTRIBUCION_DATOS.md` documenting the data architecture for chat database, user preferences, and recommendation system, including SQLite schema, data flow, and distribution patterns.

## 2025-11-29

- **Recommendation Spec**: Added `docs/RECOMMENDATION_SYSTEM.md` detailing the prompt skeleton, JSON schema, and album-plan workflow that combines Neo4j (logical brain) with Milvus (intuitive brain) plus Gemma 3. The document explains required inputs, failure handling, and how to deliver 5–10 explainable recommendations.

## 2025-11-27

- **Environment Variable Descriptions**: Updated `docs/ENVIRONMENT.md` with concise descriptions and examples for `NEO4J_DATA_DIR` and `NEO4J_BIN_PATH`, including default paths for Neo4j Desktop installations.
- **Build Command Help Enhancement**: Improved help text for the `build` command in `main.py` to include a checklist of required items and better guidance for demo builds.
- **Sampling Verification**: Confirmed that data sampling is applied during the `prepare-neo4j` step, not during `convert`, to avoid generating unnecessary full CSV files before sampling.
- **Delimiter Parsing Issue**: Identified potential issue with `DELIMITER=\t` in `.env` causing "delimiter must be a 1-character string" error; recommended using actual tab character in `.env` or ensuring proper escaping.

- **CLI Color Simplification**: Removed `utils/constants/cli_colors.py` and updated `main.py` to call `typer.colors` directly, reducing unused indirection in the command-line UX.
  - **Build Pipeline Overhaul**: `build` now runs the entire chain (TAR/TSV conversion → CSV preparation → Neo4j import → Milvus vector build) and accepts a new `--demo` flag that overrides sampling/test settings. Added reusable conversion prompts, model-gateway embedding reminders (containerized local models), deprecated `demo-build`, and introduced `CSV_CORE_DIR`, `CSV_DERIVED_DIR`, `VECTOR_LABELS`, and `DEMO_VECTOR_SAMPLE_PERCENT` environment controls with updated docs (`README.md`, `CLI_USAGE.md`, `ENVIRONMENT.md`, `.env.example`).
- **Demo Command Removal**: Removed the legacy `demo-build` command completely so help output only exposes the supported subcommands. Documentation now directs all demo usage through `build --demo`.
- **Vector Build Reliability**: Added a Bolt readiness prompt before Step 4, auto-load Milvus collections, updated search params, and ensured TEST_MODE runs embeddings over the full (already downsampled) dataset instead of re-sampling to 1%.
- **Vector Build Reliability**: Added a Bolt readiness prompt before Step 4, auto-load Milvus collections, and updated `vector_query.py` to pass the required search parameters so `build --demo` and `query` no longer fail when Neo4j or Milvus are still warming up.
- **Vector Build Auto Scaling**: The worker prompt now defaults to 75% of usable CPU cores, controlled via `VECTOR_BUILD_WORKER_PERCENT` and `VECTOR_BUILD_MAX_CORES`. Updated `.env.example` and `docs/ENVIRONMENT.md` accordingly.

## 2025-11-24

- **Memory Optimization in Data Preparation**: Fixed memory exhaustion during CSV preparation by preventing accumulation of kept node IDs when sample_fraction >= 0.9999 (full dataset). Modified `utils/files_manager/csv_helper.py` to conditionally create kept_ids sets only during sampling.
- **RAG Pipeline Fix**: Corrected graph context retrieval in `db/vector/rag_pipeline.py` by changing `n.id IN $ids` to `elementId(n) IN $ids` in Cypher query, ensuring proper matching of Neo4j element IDs from Milvus.
- **Model Configuration Refactoring**: Renamed `QWEN_GENERATE_MODEL` to `LLM_MODEL` in `.env` and code for better clarity. Ensured all models are configurable via environment variables without hardcoded defaults.
- **Model Standardization**: Confirmed use of `google/gemma-3-1b` for LLM and `text-embedding-embeddinggemma-300m-qat` for embeddings, aligned with project plan.

## 2025-11-22


## 2025-11-21

- **Documentation Updates**: Added instructions for database access in Neo4j Browser after import. Fixed CLI file references from `cli.py` to `main.py`. Removed duplicate content in `CLI_USAGE.md`. Updated deliverables in `PLAN.md` to reflect actual project files.
- **Metadata Verification Complete**: Comprehensive validation of all 7 node types and 9 relationship types in the MusicBrainz-to-Neo4j pipeline. All headers, column mappings, and data connections verified for correctness.
- **Graph Architecture Validated**: Confirmed 100% consistency between Neo4j headers and CSV preparation functions. All relationships properly connect logical music entities (Artist→Recording, Recording→Work, etc.).
- **Schema Integrity**: Validated column mappings against MusicBrainz TSV schema. All 7 node types and 9 relationship types have correct field counts and data types.
- **Relationship Expansion**: Added comprehensive relationships including genre tags (3 connections), geographic areas (2 connections), and work hierarchies. Excluded overly specific data points as requested.
- **Neo4j Import Enhancement**: Updated `neo4j_importer.py` to include all new relationship types (ReleaseGroup, Tag nodes + 6 additional relationship files) in bulk import command.
- **Data Quality Assurance**: Verified sampling compatibility, referential integrity, and exclusion of overly specific data points. Graph optimized for music recommendation use cases.
- **Metadata Verification Complete**: Comprehensive validation of all 7 node types and 9 relationship types in the MusicBrainz-to-Neo4j pipeline. All headers, column mappings, and data connections verified for correctness.
- **Graph Architecture Validated**: Confirmed 100% consistency between Neo4j headers and CSV preparation functions. All relationships properly connect logical music entities (Artist→Recording, Recording→Work, etc.).
- **Schema Integrity**: Validated column mappings against MusicBrainz TSV schema. All 7 node types and 9 relationship types have correct field counts and data types.
- **Relationship Expansion**: Added comprehensive relationships including genre tags (3 connections), geographic areas (2 connections), and work hierarchies. Excluded overly specific data points as requested.
- **Neo4j Import Enhancement**: Updated `neo4j_importer.py` to include all new relationship types (ReleaseGroup, Tag nodes + 6 additional relationship files) in bulk import command.
- **Data Quality Assurance**: Verified sampling compatibility, referential integrity, and exclusion of overly specific data points. Graph optimized for music recommendation use cases.

- **Project Pivot (clarified)**: Historical notes mentioning a pivot to Qwen 3 are superseded. The project uses Gemma-family models served locally via the `pmllm-model-gateway` (container) for both embeddings and generation. Documentation and scripts have been adjusted to rely on the gateway APIs rather than external LM Studio services.
- **Vector Database**: Selected Milvus as the production vector database for embeddings and retrieval.
- **Data Source**: Added support for fragmented MusicBrainz dataset (from PostgreSQL + Neo4j exports) as the primary data source for documents and KG relations.
- **CLI Development**: Created `cli.py` with a CLI class to extract tar files, verify TSV formats, and convert to CSV. Handles directories with mixed tar and TSV files.
- **Utils Expansion**: Extended `utils/reader.py` (now `utils/files_manager/reader.py`) with functions for delimiter detection, tabular validation, CSV conversion, and tar extraction.
- **Documentation**: Created `docs/` directory for change logs and additional documentation.
- **Large Field Support**: Updated `utils/reader.py` to lift the CSV field size limit so MusicBrainz annotation files convert without errors.

## 2025-11-19

- **CLI Modularization**: Refactored `cli.py` to delegate TSV-to-CSV conversion to `utils/files_manager/converter.py` and to add subcommands (`convert`, `prepare-neo4j`, `import-neo4j`).
- **MusicBrainz Prep CLI**: Extended `utils/files_manager/csv_helper.py` and the `prepare-neo4j` subcommand to parameterize MusicBrainz source, header, label, and relationship directories via CLI flags.
- **Neo4j Import Helper**: Added `db/neo4j/neo4j_importer.py` to wrap `neo4j-admin database import full` and `cypher-shell` verification queries.
- **Neo4j Import CLI**: Added `import-neo4j` subcommand to `cli.py` to run bulk import using generated headers/labels/relationships, with flags for directories, database name, and optional verification queries.
- **Documentation Updates**: Updated `README.md` and `plan/PLAN.md` to reflect the new CLI capabilities and renamed `docs/CHANGES.md` to `docs/CHANGELOG.md`.
- **Generator note**: References to a Qwen-based generator in earlier entries are legacy; current implementation targets Gemma models (served via the gateway) and local-container APIs. If Qwen-based experiments exist in git history, they are kept for provenance but are not the active configuration.

## 2025-11-20

- **Sampling-Friendly CSV Prep**: `utils/files_manager/csv_helper.py` now supports deterministic row sampling with CLI flags `--sample-percent` and `--sample-seed`, trimming both nodes and relationships consistently for partial Neo4j imports.
- **Legacy Neo4j Import Mode**: Added `--legacy-import` to `cli.py import-neo4j`, plus robust data-directory detection (bin-path derived, env overrides, Docker paths) inside `db/neo4j/neo4j_importer.py` so older `neo4j-admin import` workflows remain supported.
- **Type Safety & Tooling**: Introduced a project-level `mypy.ini`, resolved annotation gaps in `db/neo4j/neo4j_handler.py`, `utils/files_manager/reader.py`, embedding helpers, and RAG pipeline. `uvx mypy` now passes with explicit package bases and missing-import suppression for third-party SDKs.
- **RAG Reliability Improvements**: Hardened `db/vector/rag_pipeline.py` and `db/vector/helper/embedder.py` with structured response validation, request timeouts, and explicit list-based embeddings to avoid runtime shape mismatches.
- **Plan Alignment**: Updated `plan/PLAN.md` to mark Stage 2.1 (Neo4j KG import) as in progress and to record the new sampling/legacy import capabilities required for Stage 2 acceptance.

