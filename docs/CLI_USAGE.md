# MusicBrainz Data Preparation CLI Usage Guide

This guide provides comprehensive instructions for using the `pmllm` CLI tool to prepare MusicBrainz data for Neo4j import and perform the full build process.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Full Build Process](#full-build-process)
- [Usage Examples](#usage-examples)

## Overview

The `pmllm` CLI tool provides a complete pipeline for transforming raw MusicBrainz TSV files into Neo4j-compatible format. It supports:

- **TSV to CSV Conversion**: Extract and convert MusicBrainz dump files
- **Data Preparation**: Generate headers, labels, and relationships for Neo4j
- **Neo4j Import**: Bulk import prepared data into Neo4j database
- **Full Build Process**: Automated end-to-end pipeline with configuration files
- **7 Node Types**: Artist, Recording, Release, Work, Area, ReleaseGroup, Tag
- **9 Relationship Types**: Artist-Recording, Artist-Release, Recording-Work, etc.
- **Smart Sampling**: Maintains referential integrity during data reduction
- **Graph Validation**: Post-processing integrity checks
- **Multiple Modes**: Testing (50%) and Production (100%) configurations

## Installation

Ensure you have Python 3.10+ and the required dependencies:

```bash
# Install dependencies
pip install -r requirements.txt

# Or using the project
pip install -e .
```

## Quick Start

### Demo Build (Minimal Dataset)

```bash
# Copy and configure the environment file
cp .env.example .env
# Edit .env with your paths and settings

# Run the complete demo pipeline (0.1% sampling by default)
uv run python main.py build --demo
```

`build --demo` now covers conversion → preparation → Neo4j import → vector build using the model gateway embedding endpoint.

### Full Automated Build

```bash
# Copy and configure the environment file
cp .env.example .env
# Edit .env with your paths and settings

# Run the complete pipeline
uv run python main.py build
```

### Start the Stack + API Server

Bring up the dockerized services (Milvus, MinIO, model gateway) and launch the FastAPI recommender API with one command:

```bash
uv run python main.py start
```

Use `--skip-compose` if the containers are already running, or `--no-server` when you only need the dependency health checks.

### Data Build Only (Conversion + Preparation)

```bash
uv run python main.py build-data \
  --core-dir music_metadata \
  --derived-dir music_derived_metadata \
  --output-dir output
```

`build-data` converts TAR/TSV dumps to CSV (core + derived) and immediately runs the Neo4j preparation pipeline (headers, labeled data, relationships) without touching Neo4j import or the vector build. Pass `--reuse-converted/--no-reuse-converted` to control whether existing CSV working sets should be reused.

### Individual Steps

```bash
# Convert TSV files to CSV
uv run python main.py convert music_metadata --out output/converted/core
uv run python main.py convert music_derived_metadata --out output/converted/derived

# Prepare data for Neo4j
uv run python main.py prepare-neo4j \
  --core-dir output/converted/core \
  --derived-dir output/converted/derived \
  --output-dir output \
  --sample-percent 50.0

# (Optional) build Neo4j Desktop bundle
uv run python main.py prepare-desktop --output-dir output --bundle-dir output/neo4j_desktop

# Import to Neo4j
uv run python main.py import-neo4j --output-dir output --verify

# Build vector database
uv run python main.py build-vector

# Query the system
uv run python main.py query "What artists are similar to Queen?"
```

## Command Reference

### Main Commands

| Command            | Description                                                                            |
| ------------------ | -------------------------------------------------------------------------------------- |
| `build`            | Full pipeline (convert → prepare → import → vector build). Supports `--demo`           |
| `build-data`       | Convert TAR/TSV dumps and run Neo4j preparation (headers, labeled data, relationships) |
| `convert`          | Convert TSV files to CSV format                                                        |
| `prepare-neo4j`    | Generate headers, labels, and relationships from converted CSVs                        |
| `prepare-desktop`  | Merge headers + data into Neo4j Desktop–ready CSVs for drag-and-drop imports          |
| `import-neo4j`     | Run Neo4j bulk import (reads from `output/core/*`)                                     |
| `build-vector`     | Build vector database from Neo4j nodes and store embeddings in Milvus                 |
| `query`            | Query the RAG system                                                                   |
| `start`            | Start docker services (Milvus, model gateway) and launch the FastAPI server with readiness checks |

### Start Command

```bash
python main.py start [OPTIONS]
```

Turns `docker compose up -d` and the FastAPI server boot into a single command with friendly health checks.

| Option             | Default                               | Description |
| ------------------ | ------------------------------------- | ----------- |
| `--compose-file`   | `docker-compose.yml`                  | Compose file that defines Milvus, MinIO, and the model gateway |
| `--skip-compose`   | `False`                               | Assume containers are running and only perform health checks |
| `--no-server`      | `False`                               | Start/validate services but do not launch the FastAPI server |
| `--host`           | `API_HOST` \ `0.0.0.0`                | Host interface for the FastAPI server |
| `--port`           | `API_PORT` \ `8000`                   | Port the FastAPI server should bind to |
| `--reload/--no-reload` | `--no-reload`                    | Enable uvicorn auto-reload (development only) |

If any dependency is unreachable (Neo4j Bolt, Milvus, or the model gateway endpoints), the command exits with a clear error list so you know exactly what to fix.

### Build Command

```bash
python main.py build [OPTIONS]
```

**Options:**

| Option              | Default | Description                                                                 |
| ------------------- | ------- | --------------------------------------------------------------------------- |
| `--config PATH`     | `.env`  | Path to configuration file                                                   |
| `--demo/--no-demo`  | `--no-demo` | Force demo sampling + test-mode vector build (overrides several env values) |
| `--profile [PROFILE]` | prompt / `full` (non-interactive) | Choose a build profile: `full`, `demo`, `neo4j-only`, `embeddings-only`, or `conversion-only`. When omitted, the CLI prompts (and defaults to `full` if stdin is not a TTY). |

**Profiles:**

- `full`: Run the complete pipeline (convert → prepare → import → embeddings).
- `demo`: Same as `full` but forces the demo sampling overrides (`--demo` is shorthand).
- `neo4j-only`: Skip conversion/prep and run only the Neo4j bulk import using existing CSV artifacts.
- `embeddings-only`: Skip directly to the vector build; assumes Neo4j is already populated and online.
- `conversion-only`: Only perform the TAR/TSV to CSV conversion step.

### Build-Data Command

```bash
python main.py build-data [OPTIONS]
```

Combines TAR/TSV conversion and Neo4j preparation into a single call. Useful when you need fresh CSV assets but want to drive the actual Neo4j import manually later.

| Option                      | Default (env)                         | Description |
| --------------------------- | ------------------------------------- | ----------- |
| `--core-dir PATH`           | `TSV_CORE_DIR` \ `music_metadata`     | Directory containing core MusicBrainz dumps (TAR/TSV) |
| `--derived-dir PATH`        | `TSV_DERIVED_DIR` \ `music_derived_metadata` | Directory containing derived dumps |
| `--output-dir PATH`         | `OUTPUT_DIR` \ `output`               | Base directory for prepared headers/labeled/relationships |
| `--csv-core-dir PATH`       | `CSV_CORE_DIR` \ `output/converted/core` | Optional working directory for core CSV conversions |
| `--csv-derived-dir PATH`    | `CSV_DERIVED_DIR` \ `output/converted/derived` | Optional working directory for derived CSV conversions |
| `--sample-percent FLOAT`    | `SAMPLE_PERCENT` \ `100.0`            | Percentage of rows to keep during preparation |
| `--sample-seed INT`         | `SAMPLE_SEED` \ `42`                  | Deterministic sampling seed |
| `--delimiter STR`           | `DELIMITER` \ `\t`                    | Input delimiter (literal `\t` is accepted) |
| `--encoding STR`            | `ENCODING` \ `utf-8`                  | File encoding |
| `--skip-headers`            | env `SKIP_HEADERS=false`              | Skip header generation |
| `--skip-labels`             | env `SKIP_LABELS=false`               | Skip labeled CSV creation |
| `--skip-relationships`      | env `SKIP_RELATIONSHIPS=false`        | Skip relationship CSV creation |
| `--reuse-converted / --no-reuse-converted` | `--reuse-converted` | Reuse existing CSV working sets if they already exist |

### Demo Mode / Backwards Compatibility

- Prefer `uv run python main.py build --demo` for minimal builds.
- `demo-build` command was removed; use `build --demo` instead.

### Convert Command

```bash
python main.py convert [OPTIONS] PATH
```

**Arguments:**

- `PATH`: Directory containing TSV files

**Options:**

| Option       | Default   | Description                    |
| ------------ | --------- | ------------------------------ |
| `--out PATH` | `out_csv` | Output directory for CSV files |

### Prepare-Neo4j Command

```bash
python main.py prepare-neo4j [OPTIONS]
```

**Options:**

| Option                   | Default (env)       | Description |
| ------------------------ | ------------------ | ----------- |
| `--core-dir PATH`        | `TSV_CORE_DIR` \\ `music_metadata` | Directory containing the converted core CSV/TSV files |
| `--derived-dir PATH`     | `TSV_DERIVED_DIR` \\ `music_derived_metadata` | Directory containing derived CSV/TSV files (optional) |
| `--output-dir PATH`      | `OUTPUT_DIR` \\ `output` | Destination for generated `core/` and `derived/` subdirectories |
| `--sample-percent FLOAT` | `SAMPLE_PERCENT` \\ `100.0` | Percentage of rows to keep (0-100) |
| `--sample-seed INT`      | `SAMPLE_SEED` \\ `42` | Deterministic sampling seed |
| `--delimiter STR`        | `DELIMITER` \\ `\t` | Delimiter used in the source files (supports literal `\t`) |
| `--encoding STR`         | `ENCODING` \\ `utf-8` | File encoding |
| `--skip-headers`         | env `SKIP_HEADERS=false` | Skip header generation |
| `--skip-labels`          | env `SKIP_LABELS=false` | Skip labeled data generation |
| `--skip-relationships`   | env `SKIP_RELATIONSHIPS=false` | Skip relationship generation |

### Prepare-Desktop Command

```bash
python main.py prepare-desktop [OPTIONS]
```

This command copies the generated headers and data into `output/neo4j_desktop/{nodes,relationships}` with header rows attached, so Neo4j Desktop can import them via drag-and-drop.

| Option                               | Default | Description |
| ------------------------------------ | ------- | ----------- |
| `--output-dir PATH`                  | `OUTPUT_DIR` \\ `output` | Base directory that already contains `core/` + `derived/` artifacts |
| `--bundle-dir PATH`                  | `output/neo4j_desktop` | Destination folder for Desktop-ready CSVs |
| `--delimiter STR`                    | `DELIMITER` \\ `\t` | Delimiter to embed in the header rows |
| `--encoding STR`                     | `ENCODING` \\ `utf-8` | Encoding for the merged CSVs |
| `--include-derived-nodes / --no-...` | `True` | Copy labeled nodes from `derived/` if present |
| `--include-extended-relationships / --no-...` | `True` | Copy extended relationship CSVs from `derived/relationships` |

### Import-Neo4j Command

```bash
python main.py import-neo4j [OPTIONS]
```

**Options:**

| Option                      | Default (env)                    | Description |
| --------------------------- | -------------------------------- | ----------- |
| `--output-dir PATH`         | `OUTPUT_DIR` \\ `output`        | Base directory containing `core/headers`, `core/labeled`, and `core/relationships` |
| `--db-name STR`             | `DB_NAME` \\ `musicbrainz.db`   | Target Neo4j database name (without `.db` when issuing `:use`) |
| `--delimiter STR`           | `DELIMITER` \\ `\t`            | CSV delimiter handed to `neo4j-admin` |
| `--array-delimiter STR`     | `ARRAY_DELIMITER` \\ `;`        | Array field delimiter |
| `--allow-bad-relationships` | `ALLOW_BAD_RELATIONSHIPS=false` | Do not fail on dangling relationships |
| `--multiline-fields`        | `MULTILINE_FIELDS=true`         | Treat fields as multiline when importing |
| `--verify`                  | `VERIFY=false`                  | Run sanity queries after import |
| `--user STR`                | `NEO4J_USER` \\ `neo4j`        | Neo4j username for verification |
| `--password STR`            | `NEO4J_PASSWORD`                | Neo4j password |
| `--host STR`                | `NEO4J_HOST` \\ `localhost`    | Neo4j host |
| `--port INT`                | `NEO4J_PORT` \\ `7687`         | Bolt port for verification |
| `--neo4j-bin-path PATH`     | `NEO4J_BIN_PATH`                | Explicit path to the Neo4j `bin/` directory |
| `--java-home PATH`          | `JAVA_HOME`                     | Java installation to use for the import |
| `--legacy-import`           | `LEGACY_IMPORT=false`           | Use the legacy `neo4j-admin import` syntax |

**Nota sobre la base de datos Neo4j:**

Después de ejecutar la importación masiva, la base de datos se crea automáticamente. Sin embargo, para acceder a ella desde Neo4j Browser o para consultas interactivas, ejecuta estos comandos en Neo4j Browser:

```cypher
:use system
CREATE DATABASE <db-name> IF NOT EXISTS
:use <db-name>
```

Reemplaza `<db-name>` con el valor especificado en `--db-name` (sin la extensión `.db`). Por ejemplo, si usaste `--db-name musicbrainz.db`, usa `musicbrainz` en los comandos.

## Full Build Process

The `build` command automates the entire pipeline using a configuration file (`.env` format).

### Configuration File

Create a `.env` file with your settings:

```bash
# Copy from example
cp .env.example .env

# Edit with your values
nano .env
```

### Required Configuration

```bash
# Input/Output directories
TSV_CORE_DIR=/data/musicbrainz/core
TSV_DERIVED_DIR=/data/musicbrainz/derived
OUTPUT_DIR=output
CSV_CORE_DIR=${OUTPUT_DIR}/converted/core
CSV_DERIVED_DIR=${OUTPUT_DIR}/converted/derived

# Sampling (optional)
SAMPLE_PERCENT=100.0
SAMPLE_SEED=42

# Neo4j settings
DB_NAME=musicbrainz.db
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_HOST=localhost
NEO4J_PORT=7687

# Vector build
VECTOR_LABELS=Artist,Recording,Release,Tag
```

### Build Process Steps

1. **Conversion**: Extract TAR archives (if present) and convert the raw dumps pointed to by `TSV_CORE_DIR` / `TSV_DERIVED_DIR` into CSV working sets (`CSV_CORE_DIR`, `CSV_DERIVED_DIR`).
2. **Preparation**: Generate Neo4j headers, labeled rows, and relationship files in `OUTPUT_DIR/core` (optionally sampling rows for demos).
3. **Desktop bundle (optional)**: Run `prepare-desktop` to copy the prepared files into `OUTPUT_DIR/neo4j_desktop` with inline headers for the Neo4j Desktop drag-and-drop importer.
4. **Neo4j Import**: Execute `neo4j-admin database import` via `import-neo4j`, then optionally run verification queries through Bolt.
5. **Vector Build**: Stream nodes from Neo4j, request embeddings from the model gateway, and write vectors to Milvus for RAG.

### Build Output

```text
Loaded config from: .env
Starting full build process...

Step 1: Converting MusicBrainz dumps (TAR/TSV) into CSV working directories
✓ Converted 15 core file(s) to CSV.
✓ Converted 10 derived file(s) to CSV.

Step 2: Preparing headers and data for Neo4j
✓ Preparation completed!
Generated files:
  - neo4j_headers (headers)
  - labeled (labeled data)
  - relationships (relationships)

Step 3: Importing CSVs into Neo4j (neo4j-admin bulk import)
✓ Neo4j bulk import completed.
✓ Verification completed.

Step 4: Building Milvus vector database (requires the model gateway container)
✓ Vector DB build completed!

🎉 Build finished! Neo4j + Milvus are ready for RAG queries.
```

#### Post-Build: Acceso a la Base de Datos

Después de completar el proceso de construcción, la base de datos Neo4j se crea automáticamente. Para acceder a ella desde Neo4j Browser:

```cypher
:use system
CREATE DATABASE <db-name> IF NOT EXISTS
:use <db-name>
```

Donde `<db-name>` es el nombre especificado en `DB_NAME` (sin `.db`). Por defecto es `musicbrainz`.

## Usage Examples

### 1. Full Build with Default Config

```bash
python main.py build
```

### 2. Full Build with Custom Config

```bash
python main.py build --config my_config.env
```

### 3. Individual Steps for Development

```bash
# Convert files
python main.py convert /data/musicbrainz/core --out converted/core
python main.py convert /data/musicbrainz/derived --out converted/derived

# Prepare with 25% sample
python main.py prepare-neo4j \
  --core-dir converted/core \
  --derived-dir converted/derived \
  --output-dir output \
  --sample-percent 25.0 \
  --sample-seed 123

# Bundle for Neo4j Desktop (optional)
python main.py prepare-desktop --output-dir output --bundle-dir output/neo4j_desktop

# Import with verification
python main.py import-neo4j \
  --output-dir output \
  --verify \
  --password mypassword
```

### 4. Production Pipeline

```bash
# Full production build
echo "TSV_CORE_DIR=/data/mb-dump-2024/core" > .env
echo "TSV_DERIVED_DIR=/data/mb-dump-2024/derived" >> .env
echo "OUTPUT_DIR=/data/mb-dump-2024/output" >> .env
echo "SAMPLE_PERCENT=100.0" >> .env
echo "NEO4J_PASSWORD=production_password" >> .env

python main.py build
```

### 5. Testing Pipeline

```bash
# Quick test with small sample
echo "SAMPLE_PERCENT=10.0" > .env
echo "VERIFY=true" >> .env

python main.py build
```
