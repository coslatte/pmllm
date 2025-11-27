# Change Log

This file documents all changes made to the project, especially those implemented by agents.

## 2025-11-27

- **Environment Variable Descriptions**: Updated `docs/ENVIRONMENT.md` with concise descriptions and examples for `NEO4J_DATA_DIR` and `NEO4J_BIN_PATH`, including default paths for Neo4j Desktop installations.
- **Build Command Help Enhancement**: Improved help text for the `build` command in `main.py` to include a checklist of required items and better guidance for demo builds.
- **Sampling Verification**: Confirmed that data sampling is applied during the `prepare-neo4j` step, not during `convert`, to avoid generating unnecessary full CSV files before sampling.
- **Delimiter Parsing Issue**: Identified potential issue with `DELIMITER=\t` in `.env` causing "delimiter must be a 1-character string" error; recommended using actual tab character in `.env` or ensuring proper escaping.

- **CLI Color Simplification**: Removed `utils/constants/cli_colors.py` and updated `main.py` to call `typer.colors` directly, reducing unused indirection in the command-line UX.
- **Build Pipeline Overhaul**: `build` now runs the entire chain (TAR/TSV conversion → CSV preparation → Neo4j import → Milvus vector build) and accepts a new `--demo` flag that overrides sampling/test settings. Added reusable conversion prompts, LM Studio embedding reminders, deprecated `demo-build`, and introduced `CSV_CORE_DIR`, `CSV_DERIVED_DIR`, `VECTOR_LABELS`, and `DEMO_VECTOR_SAMPLE_PERCENT` environment controls with updated docs (`README.md`, `CLI_USAGE.md`, `ENVIRONMENT.md`, `.env.example`).
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

- **Model Strategy Update**: Switched text embedding model to 'text-embedding-embeddinggemma-300m-qat' (Gemma Embedding 300M, Q4_0, 229.09 MB from lmstudio-community). Updated LLM to 'google/gemma-3-1b' (Gemma 3 1B, Q4_0, 720.50 MB). This change reflects new LLM strategies for improved performance in the RAG pipeline. Updated `plan/PLAN.md` to document the new models and their specifications.
- **Documentation Enhancement**: Created `docs/CHANGELOG_es.md` as a Spanish version of the change log, mirroring all entries in Spanish. Updated `plan/PLAN.md` to include documentation in both languages when appropriate and added `docs/CHANGELOG_es.md` to deliverables.
- **Environment Configuration Update**: Updated `.env` and `docs/ENVIRONMENT.md` to reflect the new Gemma models: set `QWEN_GENERATE_MODEL` to 'google/gemma-3-1b' and `EMBEDDING_MODEL_PATH` to 'text-embedding-embeddinggemma-300m-qat'.

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

- **Project Pivot**: Switched from fine-tuning models to Retrieval-Augmented Generation (RAG) using Qwen 3 as the LLM generator. Updated `README.md`, `plan/PLAN.md`, and `plan/original_plan.md` to reflect this change.
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
- **Qwen Generator**: Updated the RAG pipeline to call `qwen/qwen3-1.7b` for generation and `text-embedding-qwen3-embedding-0.6b` for embeddings, including helper modules and documentation.

## 2025-11-20

- **Sampling-Friendly CSV Prep**: `utils/files_manager/csv_helper.py` now supports deterministic row sampling with CLI flags `--sample-percent` and `--sample-seed`, trimming both nodes and relationships consistently for partial Neo4j imports.
- **Legacy Neo4j Import Mode**: Added `--legacy-import` to `cli.py import-neo4j`, plus robust data-directory detection (bin-path derived, env overrides, Docker paths) inside `db/neo4j/neo4j_importer.py` so older `neo4j-admin import` workflows remain supported.
- **Type Safety & Tooling**: Introduced a project-level `mypy.ini`, resolved annotation gaps in `db/neo4j/neo4j_handler.py`, `utils/files_manager/reader.py`, embedding helpers, and RAG pipeline. `uvx mypy` now passes with explicit package bases and missing-import suppression for third-party SDKs.
- **RAG Reliability Improvements**: Hardened `db/vector/rag_pipeline.py` and `db/vector/helper/embedder.py` with structured response validation, request timeouts, and explicit list-based embeddings to avoid runtime shape mismatches.
- **Plan Alignment**: Updated `plan/PLAN.md` to mark Stage 2.1 (Neo4j KG import) as in progress and to record the new sampling/legacy import capabilities required for Stage 2 acceptance.

