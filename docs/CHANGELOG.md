# Change Log

This file documents all changes made to the project, especially those implemented by agents.

## 2025-11-13

- **Project Pivot**: Switched from fine-tuning models to Retrieval-Augmented Generation (RAG) using Qwen 3 as the LLM generator. Updated `README.md`, `plan/PLAN.md`, and `plan/original_plan.md` to reflect this change.
- **Vector Database**: Selected Milvus as the production vector database for embeddings and retrieval.
- **Data Source**: Added support for fragmented MusicBrainz dataset (from PostgreSQL + Neo4j exports) as the primary data source for documents and KG relations.
- **CLI Development**: Created `cli.py` with a CLI class to extract tar files, verify TSV formats, and convert to CSV. Handles directories with mixed tar and TSV files.
- **Utils Expansion**: Extended `utils/reader.py` (now `utils/file_manager/reader.py`) with functions for delimiter detection, tabular validation, CSV conversion, and tar extraction.
- **Documentation**: Created `docs/` directory for change logs and additional documentation.
- **Large Field Support**: Updated `utils/reader.py` to lift the CSV field size limit so MusicBrainz annotation files convert without errors.

## 2025-11-19

- **CLI Modularization**: Refactored `cli.py` to delegate TSV-to-CSV conversion to `utils/file_manager/converter.py` and to add subcommands (`convert`, `prepare-neo4j`, `import-neo4j`).
- **MusicBrainz Prep CLI**: Extended `utils/file_manager/csv_helper.py` and the `prepare-neo4j` subcommand to parameterize MusicBrainz source, header, label, and relationship directories via CLI flags.
- **Neo4j Import Helper**: Added `db/neo4j/neo4j_importer.py` to wrap `neo4j-admin database import full` and `cypher-shell` verification queries.
- **Neo4j Import CLI**: Added `import-neo4j` subcommand to `cli.py` to run bulk import using generated headers/labels/relationships, with flags for directories, database name, and optional verification queries.
- **Documentation Updates**: Updated `README.md` and `plan/PLAN.md` to reflect the new CLI capabilities and renamed `docs/CHANGES.md` to `docs/CHANGELOG.md`.
- **Qwen Generator**: Updated the RAG pipeline to call `qwen/qwen3-1.7b` for generation and `text-embedding-qwen3-embedding-0.6b` for embeddings, including helper modules and documentation.

## 2025-11-20

- **Sampling-Friendly CSV Prep**: `utils/file_manager/csv_helper.py` now supports deterministic row sampling with CLI flags `--sample-percent` and `--sample-seed`, trimming both nodes and relationships consistently for partial Neo4j imports.
- **Legacy Neo4j Import Mode**: Added `--legacy-import` to `cli.py import-neo4j`, plus robust data-directory detection (bin-path derived, env overrides, Docker paths) inside `db/neo4j/neo4j_importer.py` so older `neo4j-admin import` workflows remain supported.
- **Type Safety & Tooling**: Introduced a project-level `mypy.ini`, resolved annotation gaps in `db/neo4j/neo4j_handler.py`, `utils/file_manager/reader.py`, embedding helpers, and RAG pipeline. `uvx mypy` now passes with explicit package bases and missing-import suppression for third-party SDKs.
- **RAG Reliability Improvements**: Hardened `db/vector/rag_pipeline.py` and `db/vector/helper/embedder.py` with structured response validation, request timeouts, and explicit list-based embeddings to avoid runtime shape mismatches.
- **Plan Alignment**: Updated `plan/PLAN.md` to mark Stage 2.1 (Neo4j KG import) as in progress and to record the new sampling/legacy import capabilities required for Stage 2 acceptance.
