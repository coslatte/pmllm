# MusicBrainz Data Preparation CLI Usage Guide

This guide provides comprehensive instructions for using the `pmllm` CLI tool to prepare MusicBrainz data for Neo4j import and perform the full build process.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Full Build Process](#full-build-process)
- [Usage Examples](#usage-examples)
- [Sampling Strategies](#sampling-strategies)
- [Validation Features](#validation-features)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

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

`build --demo` now covers conversion → preparation → Neo4j import → vector build using LM Studio's embedding endpoint.

### Full Automated Build

```bash
# Copy and configure the environment file
cp .env.example .env
# Edit .env with your paths and settings

# Run the complete pipeline
uv run python main.py build
```

### Individual Steps

```bash
# Convert TSV files to CSV
uv run python main.py convert mbdump --out out_csv

# Prepare data for Neo4j
uv run python main.py prepare-neo4j --sample-percent 50.0

# Import to Neo4j
uv run python main.py import-neo4j --verify

# Build vector database
uv run python main.py build-vector

# Query the system
uv run python main.py query "What artists are similar to Queen?"
```

## Command Reference

### Main Commands

| Command         | Description                                                           |
| --------------- | --------------------------------------------------------------------- |
| `build`         | Full pipeline (convert → prepare → import → vector build). Supports `--demo` |
| `convert`       | Convert TSV files to CSV format                       |
| `prepare-neo4j` | Generate headers, labels, and relationships           |
| `import-neo4j`  | Run Neo4j bulk import                                 |
| `build-vector`  | Build vector database from Neo4j nodes                |
| `query`         | Query the RAG system                                 |

### Build Command

```bash
python main.py build [OPTIONS]
```

**Options:**

| Option              | Default | Description                                                                 |
| ------------------- | ------- | --------------------------------------------------------------------------- |
| `--config PATH`     | `.env`  | Path to configuration file                                                   |
| `--demo/--no-demo`  | `--no-demo` | Force demo sampling + test-mode vector build (overrides several env values) |

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

| Option                    | Default         | Description                          |
| ------------------------- | --------------- | ------------------------------------ |
| `--mbdump DIR`            | `mbdump`        | Directory with MusicBrainz TSV files |
| `--headers-dir DIR`       | `neo4j_headers` | Output directory for headers         |
| `--labeled-dir DIR`       | `labeled`       | Output directory for labeled data    |
| `--relationships-dir DIR` | `relationships` | Output directory for relationships   |
| `--sample-percent FLOAT`  | `100.0`         | Sample percentage (0-100)            |
| `--sample-seed INT`       | `42`            | Random seed for sampling             |
| `--delimiter STR`         | `\t`            | Input file delimiter                 |
| `--encoding STR`          | `utf-8`         | File encoding                        |
| `--skip-headers`          | -               | Skip header generation               |
| `--skip-labels`           | -               | Skip labeled data generation         |
| `--skip-relationships`    | -               | Skip relationship generation         |

### Import-Neo4j Command

```bash
python main.py import-neo4j [OPTIONS]
```

**Options:**

| Option                      | Default          | Description                |
| --------------------------- | ---------------- | -------------------------- |
| `--headers-dir DIR`         | `neo4j_headers`  | Headers directory          |
| `--labeled-dir DIR`         | `labeled`        | Labeled data directory     |
| `--relationships-dir DIR`   | `relationships`  | Relationships directory    |
| `--db-name STR`             | `musicbrainz.db` | Neo4j database name        |
| `--delimiter STR`           | `\t`             | CSV delimiter              |
| `--array-delimiter STR`     | `;`              | Array field delimiter      |
| `--allow-bad-relationships` | -                | Allow broken relationships |
| `--multiline-fields`        | `True`           | Treat fields as multiline  |
| `--verify`                  | -                | Run verification queries   |
| `--user STR`                | `neo4j`          | Neo4j username             |
| `--password STR`            | -                | Neo4j password             |
| `--host STR`                | `localhost`      | Neo4j host                 |
| `--port INT`                | `7687`           | Neo4j port                 |
| `--neo4j-bin-path PATH`     | -                | Neo4j bin directory        |
| `--java-home PATH`          | -                | Java home directory        |
| `--legacy-import`           | -                | Use legacy import          |

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
TSV_DIR=mbdump
CSV_OUT_DIR=out_csv
HEADERS_DIR=neo4j_headers
LABELED_DIR=labeled
RELATIONSHIPS_DIR=relationships

# Sampling (optional)
SAMPLE_PERCENT=100.0
SAMPLE_SEED=42

# Neo4j settings
DB_NAME=musicbrainz.db
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_HOST=localhost
NEO4J_PORT=7687
```

### Build Process Steps

1. **Conversion**: Extract TAR archives (if present) and convert TSV files to CSV working sets (`CSV_CORE_DIR`, `CSV_DERIVED_DIR`).
2. **Preparation**: Generates Neo4j headers, labeled rows, and relationship files with optional sampling.
3. **Neo4j Import**: Performs `neo4j-admin` bulk import plus optional verification queries.
4. **Vector Build**: Streams nodes from Neo4j, builds LM Studio embeddings, and writes vectors to Milvus for RAG.

### Build Output

```
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

Step 4: Building Milvus vector database (requires LM Studio embedding model)
✓ Vector DB build completed!

🎉 Build finished! Neo4j + Milvus are ready for RAG queries.
```

**Post-Build: Acceso a la Base de Datos**

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
python main.py convert /data/musicbrainz --out converted_csv

# Prepare with 25% sample
python main.py prepare-neo4j \
  --mbdump /data/musicbrainz \
  --sample-percent 25.0 \
  --sample-seed 123

# Import with verification
python main.py import-neo4j \
  --verify \
  --password mypassword
```

### 4. Production Pipeline

```bash
# Full production build
echo "TSV_DIR=/data/mb-dump-2024" > .env
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
