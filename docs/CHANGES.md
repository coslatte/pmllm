# Change Log

This file documents all changes made to the project, especially those implemented by agents.

## 2025-11-13

- **Project Pivot**: Switched from fine-tuning models to Retrieval-Augmented Generation (RAG) using Gemma 3 as the LLM generator. Updated `README.md`, `plan/PLAN.md`, and `plan/original_plan.md` to reflect this change.
- **Vector Database**: Selected Milvus as the production vector database for embeddings and retrieval.
- **Data Source**: Added support for fragmented MusicBrainz dataset (from PostgreSQL + Neo4j exports) as the primary data source for documents and KG relations.
- **CLI Development**: Created `cli.py` with a CLI class to extract tar files, verify TSV formats, and convert to CSV. Handles directories with mixed tar and TSV files.
- **Utils Expansion**: Extended `utils/reader.py` with functions for delimiter detection, tabular validation, CSV conversion, and tar extraction.
- **Documentation**: Created `docs/` directory for change logs and additional documentation.

## Future Changes

- Add console script entry in `pyproject.toml` for easier CLI usage.
- Implement ingestion scripts to populate Milvus with embeddings from converted CSVs.
- Add unit tests for new utilities.
