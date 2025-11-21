# Environment Variables Configuration

This document provides detailed information about all environment variables used in the MusicBrainz-to-Neo4j pipeline.

## Quick Start

Copy `.env.example` to `.env` and modify the values according to your setup:

```bash
cp .env.example .env
# Edit .env with your specific values
```

## Variable Categories

### Neo4j Connection Settings

| Variable               | Default                 | Description                                                                             |
| ---------------------- | ----------------------- | --------------------------------------------------------------------------------------- |
| `NEO4J_URI`            | `bolt://localhost:7687` | Neo4j connection URI. Use `bolt://` for secure connections or `neo4j://` for clustering |
| `NEO4J_USER`           | `neo4j`                 | Neo4j database username                                                                 |
| `NEO4J_PASSWORD`       | `your_password_here`    | Neo4j database password. Required for authentication                                    |
| `NEO4J_ALLOW_INSECURE` | `false`                 | Allow connections with default password. Only for development/testing                   |
| `NEO4J_DATA_DIR`       | -                       | Path to Neo4j data directory for local bulk imports                                     |

### Milvus Vector Database Settings

| Variable      | Default     | Description                          |
| ------------- | ----------- | ------------------------------------ |
| `MILVUS_HOST` | `127.0.0.1` | Milvus server hostname or IP address |
| `MILVUS_PORT` | `19530`     | Milvus server port number            |

### MinIO Object Storage

| Variable           | Default      | Description                         |
| ------------------ | ------------ | ----------------------------------- |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key for authentication |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key for authentication |

**Security Warning:** Change MinIO credentials for production use!

### LLM API Settings

| Variable              | Default                                     | Description                                        |
| --------------------- | ------------------------------------------- | -------------------------------------------------- |
| `QWEN_GENERATE_URL`   | `http://localhost:1234/v1/chat/completions` | Endpoint URL for LLM API (LM Studio or compatible) |
| `QWEN_GENERATE_MODEL` | `qwen-1.7b`                                 | Model name to use for text generation              |

### Embedding Model Settings

| Variable               | Default                               | Description                                                          |
| ---------------------- | ------------------------------------- | -------------------------------------------------------------------- |
| `EMBEDDING_MODEL_PATH` | `Alibaba-NLP/gte-Qwen2-1.5B-instruct` | Path to embedding model. Can be HuggingFace model name or local path |

## Build Process Configuration

### Input/Output Directories

| Variable          | Default               | Description                                                                 |
| ----------------- | --------------------- | --------------------------------------------------------------------------- |
| `OUTPUT_DIR`      | `output`              | Base output directory. Automatically creates `core/` and `derived/` subdirectories |
| `TSV_CORE_DIR`    | `music_metadata`      | Directory containing core MusicBrainz TSV files (artists, recordings, releases, etc.) |
| `TSV_DERIVED_DIR` | `music_derived_metadata` | Directory containing derived MusicBrainz TSV files (labels, places, events, etc.) |

### Sampling Options

| Variable         | Default | Description                                                             |
| ---------------- | ------- | ----------------------------------------------------------------------- |
| `SAMPLE_PERCENT` | `100.0` | Percentage of data to process (0.0-100.0). Use lower values for testing |
| `SAMPLE_SEED`    | `42`    | Random seed for reproducible sampling. Ensures consistent results       |

### File Processing Options

| Variable             | Default | Description                                        |
| -------------------- | ------- | -------------------------------------------------- |
| `DELIMITER`          | `\t`    | Field delimiter in input TSV files (tab character) |
| `ENCODING`           | `utf-8` | Character encoding of input files                  |
| `SKIP_HEADERS`       | `false` | Skip generation of Neo4j header files              |
| `SKIP_LABELS`        | `false` | Skip processing of labeled node data               |
| `SKIP_RELATIONSHIPS` | `false` | Skip processing of relationship data               |

## Derived Data Processing Options

The pipeline supports processing additional MusicBrainz "derived" data to create a richer knowledge graph. These options control which additional entity types and relationships to include. Derived data adds context and connections beyond the core artist/release/recording data.

### Core Derived Entities

These add fundamental music industry entities to the graph, providing richer context for music data:

| Variable              | Default | Description                                                                              |
| --------------------- | ------- | ---------------------------------------------------------------------------------------- |
| `PROCESS_LABELS`      | `true`  | Record labels (Sony, Universal, etc.). Adds industry context and business relationships  |
| `PROCESS_MEDIUMS`     | `true`  | Physical media types (CD, Vinyl, Digital). Describes release formats and carriers        |
| `PROCESS_TRACKS`      | `true`  | Individual tracks within releases. Provides detailed track-level information             |
| `PROCESS_PLACES`      | `true`  | Recording locations, venues. Adds geographic and performance context                     |
| `PROCESS_EVENTS`      | `true`  | Concerts, festivals, events. Links artists to their performances and tours               |
| `PROCESS_GENRES`      | `true`  | Music genres. Enables genre-based queries and recommendations                            |
| `PROCESS_INSTRUMENTS` | `true`  | Musical instruments. Shows artist specializations and performance details                |
| `PROCESS_SERIES`      | `true`  | Album/Artist series. Groups related releases and connects collections                    |
| `PROCESS_URLS`        | `true`  | External links (Wikipedia, official sites). Provides additional resources and references |

### Metadata Enrichment

These add detailed metadata and classifications that enhance entity information:

| Variable             | Default | Description                                                                    |
| -------------------- | ------- | ------------------------------------------------------------------------------ |
| `PROCESS_ALIASES`    | `true`  | Alternative names for entities. Improves search and handles name variations    |
| `PROCESS_TYPES`      | `true`  | Entity type classifications. Adds type information for better categorization   |
| `PROCESS_ATTRIBUTES` | `true`  | Additional properties and characteristics. Enriches entity metadata            |
| `PROCESS_CREDITS`    | `true`  | Artist credits and contributions. Shows detailed attribution and roles         |
| `PROCESS_LANGUAGES`  | `true`  | Work languages, release countries. Adds localization and regional information  |
| `PROCESS_PACKAGING`  | `true`  | Release packaging types. Describes physical release formats                    |
| `PROCESS_STATUSES`   | `true`  | Release statuses (Official, Bootleg). Indicates content quality and legitimacy |

### Extended Relationships

| Variable                         | Default | Description                                                                        |
| -------------------------------- | ------- | ---------------------------------------------------------------------------------- |
| `PROCESS_EXTENDED_RELATIONSHIPS` | `true`  | Process additional l\_\* relationship files. Adds complex inter-entity connections |
| `RELATIONSHIPS_TO_SKIP`          | -       | Comma-separated list of relationships to exclude. Useful for performance tuning    |
| `QUIET_MISSING_EXTENDED_RELATIONSHIPS` | `false` | Suppress warnings when optional l\_\* tables are absent in the provided dumps         |

**Example:** `RELATIONSHIPS_TO_SKIP=l_artist_event,l_genre_genre,l_url_work`

### Advanced Options

These are specialized options, usually disabled as they require specific use cases:

| Variable            | Default | Description                                                                               |
| ------------------- | ------- | ----------------------------------------------------------------------------------------- |
| `PROCESS_REDIRECTS` | `false` | GID redirects for data cleanup. Used for database maintenance and deduplication           |
| `PROCESS_ISNI_IPI`  | `false` | ISNI/IPI professional identifiers. For industry integration and professional verification |
| `PROCESS_ISRC_ISWC` | `false` | ISRC/ISWC recording/work codes. For rights management and content identification          |
| `PROCESS_CDTOC`     | `false` | CD Table of Contents. For CD identification and audio matching                            |

## Neo4j Import Options

### Database Configuration

| Variable                  | Default | Description                                                               |
| ------------------------- | ------- | ------------------------------------------------------------------------- |
| `DB_NAME`                 | -       | Name of the Neo4j database to create. Leave empty to use default database |
| `ARRAY_DELIMITER`         | `;`     | Delimiter for array fields in CSV data                                    |
| `ALLOW_BAD_RELATIONSHIPS` | `false` | Allow relationships with missing nodes. May create orphaned relationships |
| `MULTILINE_FIELDS`        | `true`  | Support multiline field values in CSV data                                |
| `VERIFY`                  | `true`  | Run verification queries after import to check data integrity             |

### Connection for Verification

| Variable     | Default     | Description                         |
| ------------ | ----------- | ----------------------------------- |
| `NEO4J_HOST` | `localhost` | Neo4j host for verification queries |
| `NEO4J_PORT` | `7687`      | Neo4j port for verification queries |

## Optional Paths

### Neo4j Installation Paths

| Variable         | Description                                      | Example (Windows)                                      | Example (Linux/Mac)            |
| ---------------- | ------------------------------------------------ | ------------------------------------------------------ | ------------------------------ |
| `NEO4J_BIN_PATH` | Path to Neo4j bin directory for bulk import tool | `C:\Users\User\.Neo4jDesktop2\Data\dbmss\dbms-xxx\bin` | `/path/to/neo4j/bin`           |
| `JAVA_HOME`      | Path to Java installation directory              | Check `$env:JAVA_HOME` in PowerShell                   | Check `$JAVA_HOME` in terminal |
| `LEGACY_IMPORT`  | Use legacy import for Neo4j versions < 5.0       | `false`                                                | `false`                        |

## Configuration Examples

### Development Setup

Minimal configuration for local development and testing:

```bash
# Basic Neo4j connection
NEO4J_PASSWORD=password123

# Use small sample for faster processing
SAMPLE_PERCENT=10.0

# Disable extended relationships for speed
PROCESS_EXTENDED_RELATIONSHIPS=false
```

### Production Setup

Complete configuration for production use with full data processing:

```bash
# Secure Neo4j connection
NEO4J_PASSWORD=your_secure_password

# Process all data
SAMPLE_PERCENT=100.0

# Enable all derived data for rich graph
PROCESS_LABELS=true
PROCESS_MEDIUMS=true
PROCESS_TRACKS=true
PROCESS_PLACES=true
PROCESS_EVENTS=true
PROCESS_GENRES=true
PROCESS_INSTRUMENTS=true
PROCESS_SERIES=true
PROCESS_URLS=true
PROCESS_EXTENDED_RELATIONSHIPS=true

# Specify database name
DB_NAME=musicbrainz_full
```

### Minimal Graph Setup

Configuration for basic functionality with only core entities:

```bash
# Process half the data
SAMPLE_PERCENT=50.0

# Disable all derived data for minimal graph
PROCESS_LABELS=false
PROCESS_MEDIUMS=false
PROCESS_TRACKS=false
PROCESS_PLACES=false
PROCESS_EVENTS=false
PROCESS_GENRES=false
PROCESS_INSTRUMENTS=false
PROCESS_SERIES=false
PROCESS_URLS=false
PROCESS_EXTENDED_RELATIONSHIPS=false
```

## Troubleshooting

### Common Issues

1. **"File not found" errors**:

   - Check that `TSV_DIR` points to the correct MusicBrainz dump directory
   - Ensure all required TSV files are present in the directory
   - Verify file permissions allow reading

2. **Memory issues**:

   - Reduce `SAMPLE_PERCENT` to process less data
   - Disable some `PROCESS_*` options to reduce memory usage
   - Consider increasing system RAM or using a smaller dataset

3. **Import failures**:

   - Check Neo4j logs for detailed error messages
   - Ensure `NEO4J_BIN_PATH` points to the correct Neo4j installation
   - Verify Java is installed and `JAVA_HOME` is set correctly
   - Check available disk space for the import process

4. **Encoding errors**:

   - Verify that MusicBrainz files use UTF-8 encoding
   - Check `ENCODING` setting matches your file encoding
   - Some older dumps may use different encodings

5. **Connection errors**:
   - Verify Neo4j is running and accessible
   - Check `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`
   - Ensure firewall allows connections to Neo4j port

### Performance Tuning

- **For development**: Use `SAMPLE_PERCENT=10.0` and disable derived data processing for faster iteration
- **For testing**: Use `SAMPLE_PERCENT=50.0` with selective derived data to balance speed and completeness
- **For production**: Use `SAMPLE_PERCENT=100.0` with all features enabled for complete data processing

### Validation

After configuration, test with:

```bash
python cli.py prepare-neo4j --mode testing
```

This will process a small sample and validate your configuration without full import.
