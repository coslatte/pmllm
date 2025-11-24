# Environment Variables Configuration

## Overview

The pmllm system uses environment variables for all configuration. Copy `.env.example` to `.env` and modify as needed.

## Core Variables

### Neo4j Database

- `NEO4J_URI`: Connection URI (default: bolt://localhost:7687)
- `NEO4J_USER`: Username (default: neo4j)
- `NEO4J_PASSWORD`: Password (required)
- `NEO4J_DATABASE`: Database name (default: pmllmdb)

### Milvus Vector Database

- `MILVUS_HOST`: Host (default: 127.0.0.1)
- `MILVUS_PORT`: Port (default: 19530)

### LLM Configuration

- `QWEN_GENERATE_URL`: LM Studio API URL (default: http://127.0.0.1:1234/v1/chat/completions)
- `LLM_MODEL`: Model name (default: google/gemma-3-1b)

### Embedding Configuration

- `USE_LOCAL_EMBEDDING`: Use local SentenceTransformer (default: false)
- `EMBEDDING_MODEL`: Model name (default: text-embedding-embeddinggemma-300m-qat)
- `EMBEDDING_URL`: LM Studio embeddings URL (default: http://127.0.0.1:1234/v1/embeddings)

## Data Processing Variables

### Paths

- `OUTPUT_DIR`: Output directory for processed files
- `TSV_CORE_DIR`: Core MusicBrainz TSV files
- `TSV_DERIVED_DIR`: Derived MusicBrainz TSV files

### Sampling

- `SAMPLE_PERCENT`: Percentage of data to process (default: 1.0)
- `SAMPLE_SEED`: Random seed for sampling (default: 42)

### Processing Options

- `PROCESS_LABELS`: Include record labels (default: true)
- `PROCESS_MEDIUMS`: Include media types (default: true)
- `PROCESS_TRACKS`: Include tracks (default: true)
- `PROCESS_PLACES`: Include places (default: true)
- `PROCESS_EVENTS`: Include events (default: true)
- `PROCESS_GENRES`: Include genres (default: true)
- `PROCESS_INSTRUMENTS`: Include instruments (default: true)
- `PROCESS_SERIES`: Include series (default: true)
- `PROCESS_URLS`: Include URLs (default: true)

## Build Configuration

- `VECTOR_BUILD_WORKERS`: Number of workers for vector building (default: 12)
- `VECTOR_BUILD_SAMPLE_PERCENT`: Sampling for vector build (default: 100.0)
- `TEST_MODE`: Enable test mode (default: true)
- `TEST_SAMPLE_PERCENT`: Test sampling percentage (default: 1.0)
