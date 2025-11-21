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

### Full Automated Build

```bash
# Copy and configure the environment file
cp .env.example .env
# Edit .env with your paths and settings

# Run the complete pipeline
python cli.py build
```

### Individual Steps

```bash
# Convert TSV files to CSV
python cli.py convert mbdump --out out_csv

# Prepare data for Neo4j
python cli.py prepare-neo4j --sample-percent 50.0

# Import to Neo4j
python cli.py import-neo4j --verify
```

## Command Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `build` | Run the complete pipeline: convert → prepare → import |
| `convert` | Convert TSV files to CSV format |
| `prepare-neo4j` | Generate headers, labels, and relationships |
| `import-neo4j` | Run Neo4j bulk import |

### Build Command

```bash
python cli.py build [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` | `.env` | Path to configuration file |

### Convert Command

```bash
python cli.py convert [OPTIONS] PATH
```

**Arguments:**

- `PATH`: Directory containing TSV files

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--out PATH` | `out_csv` | Output directory for CSV files |

### Prepare-Neo4j Command

```bash
python cli.py prepare-neo4j [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--mbdump DIR` | `mbdump` | Directory with MusicBrainz TSV files |
| `--headers-dir DIR` | `neo4j_headers` | Output directory for headers |
| `--labeled-dir DIR` | `labeled` | Output directory for labeled data |
| `--relationships-dir DIR` | `relationships` | Output directory for relationships |
| `--sample-percent FLOAT` | `100.0` | Sample percentage (0-100) |
| `--sample-seed INT` | `42` | Random seed for sampling |
| `--delimiter STR` | `\t` | Input file delimiter |
| `--encoding STR` | `utf-8` | File encoding |
| `--skip-headers` | - | Skip header generation |
| `--skip-labels` | - | Skip labeled data generation |
| `--skip-relationships` | - | Skip relationship generation |

### Import-Neo4j Command

```bash
python cli.py import-neo4j [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--headers-dir DIR` | `neo4j_headers` | Headers directory |
| `--labeled-dir DIR` | `labeled` | Labeled data directory |
| `--relationships-dir DIR` | `relationships` | Relationships directory |
| `--db-name STR` | `musicbrainz.db` | Neo4j database name |
| `--delimiter STR` | `\t` | CSV delimiter |
| `--array-delimiter STR` | `;` | Array field delimiter |
| `--allow-bad-relationships` | - | Allow broken relationships |
| `--multiline-fields` | `True` | Treat fields as multiline |
| `--verify` | - | Run verification queries |
| `--user STR` | `neo4j` | Neo4j username |
| `--password STR` | - | Neo4j password |
| `--host STR` | `localhost` | Neo4j host |
| `--port INT` | `7687` | Neo4j port |
| `--neo4j-bin-path PATH` | - | Neo4j bin directory |
| `--java-home PATH` | - | Java home directory |
| `--legacy-import` | - | Use legacy import |

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

1. **TSV Conversion**: Converts all TSV files to CSV format
2. **Header Extraction**: Generates Neo4j-compatible headers
3. **Data Preparation**: Creates labeled data and relationships
4. **Neo4j Import**: Performs bulk import into Neo4j
5. **Verification**: Runs integrity checks (if enabled)

### Build Output

```
Loaded config from: .env
Starting full build process...

Step 1: Converting TSV to CSV
✓ Converted 15 file(s) to: out_csv

Step 2: Preparing headers and data for Neo4j
✓ Preparation completed!
Generated files:
  - neo4j_headers (headers)
  - labeled (labeled data)
  - relationships (relationships)

Step 3: Importing to Neo4j
✓ Neo4j bulk import completed.
✓ Verification completed.

🎉 Full build process completed successfully!
```

## Usage Examples

### 1. Full Build with Default Config

```bash
python cli.py build
```

### 2. Full Build with Custom Config

```bash
python cli.py build --config my_config.env
```

### 3. Individual Steps for Development

```bash
# Convert files
python cli.py convert /data/musicbrainz --out converted_csv

# Prepare with 25% sample
python cli.py prepare-neo4j \
  --mbdump /data/musicbrainz \
  --sample-percent 25.0 \
  --sample-seed 123

# Import with verification
python cli.py import-neo4j \
  --verify \
  --password mypassword
```

### 4. Production Pipeline

```bash
# Full production build
echo "TSV_DIR=/data/mb-dump-2024" > .env
echo "SAMPLE_PERCENT=100.0" >> .env
echo "NEO4J_PASSWORD=production_password" >> .env

python cli.py build
```

### 5. Testing Pipeline

```bash
# Quick test with small sample
echo "SAMPLE_PERCENT=10.0" > .env
echo "VERIFY=true" >> .env

python cli.py build
```

## Installation

Ensure you have Python 3.10+ and the required dependencies:

```bash
# Install dependencies
pip install -r requirements.txt

# Or using the project
pip install -e .
```

## Quick Start

### Basic Usage (Production Mode)

```bash
# Prepare full dataset for production
python utils/files_manager/csv_helper.py \
  --mode production \
  --validate-sampling
```

### Development/Testing Mode

```bash
# Prepare 50% sample for faster development
python utils/files_manager/csv_helper.py \
  --mode testing \
  --validate-sampling
```

### Custom Sampling

```bash
# Use 25% sample with custom seed
python utils/files_manager/csv_helper.py \
  --sample-percent 0.25 \
  --sample-seed 12345 \
  --validate-sampling
```

## Command Reference

### Main Command

```bash
python utils/files_manager/csv_helper.py [OPTIONS]
```

### Directory Options

| Option                    | Default         | Description                                       |
| ------------------------- | --------------- | ------------------------------------------------- |
| `--mbdump DIR`            | `mbdump`        | Directory containing MusicBrainz TSV source files |
| `--headers-dir DIR`       | `neo4j_headers` | Output directory for Neo4j header CSV files       |
| `--labeled-dir DIR`       | `labeled`       | Output directory for labeled data CSV files       |
| `--relationships-dir DIR` | `relationships` | Output directory for relationship CSV files       |

### Processing Options

| Option                 | Description                      |
| ---------------------- | -------------------------------- |
| `--skip-headers`       | Skip header CSV generation       |
| `--skip-labels`        | Skip labeled data generation     |
| `--skip-relationships` | Skip relationship CSV generation |

### Sampling Options

| Option                        | Default | Description                                            |
| ----------------------------- | ------- | ------------------------------------------------------ |
| `--mode {testing,production}` | -       | Operation mode: `testing` (50%) or `production` (100%) |
| `--sample-percent FLOAT`      | -       | Custom sample percentage (0.0-1.0). Overrides `--mode` |
| `--sample-seed INT`           | `42`    | Random seed for reproducible sampling                  |

### Validation Options

| Option                | Description                                  |
| --------------------- | -------------------------------------------- |
| `--validate-sampling` | Run post-sampling graph integrity validation |

### General Options

| Option             | Default | Description                       |
| ------------------ | ------- | --------------------------------- |
| `--delimiter CHAR` | `\t`    | Field delimiter in input files    |
| `--encoding STR`   | `utf-8` | Text encoding for reading/writing |
| `-h, --help`       | -       | Show help message and exit        |

## Usage Examples

### 1. Production Pipeline (Complete Dataset)

```bash
python utils/files_manager/csv_helper.py \
  --mode production \
  --validate-sampling \
  --mbdump /path/to/musicbrainz/data \
  --headers-dir neo4j_headers \
  --labeled-dir labeled_data \
  --relationships-dir relationships
```

**Output:**

```
🏭 PRODUCTION MODE: Using 100% data for complete dataset
🎲 Sample seed: 42
Preparing MusicBrainz data for Neo4j...

✅ Header files created in /path/to/headers
✅ Label added to artist -> labeled_artist.csv
✅ Label added to recording -> labeled_recording.csv
[...]

Preparation completed!

Generated files:
  - /path/to/headers (header directory)
  - /path/to/labeled (labeled data)
  - /path/to/relationships (relationship files)

============================================================
🔍 Validating sampling integrity...

📊 Integrity Score: 100.0% (✅ GOOD)
🔗 Total Relationships: 1,234,567
❌ Broken Relationships: 0

📋 VALIDATION SUMMARY:
   Status: ✅ GOOD
   Integrity Score: 100.0%
   Total Relationships: 1,234,567
   Broken Relationships: 0

✅ Graph integrity validated successfully!
```

### 2. Development Pipeline (50% Sample)

```bash
python utils/files_manager/csv_helper.py \
  --mode testing \
  --validate-sampling
```

**Output:**

```
🧪 TESTING MODE: Using 50% sample for faster development cycles
🎲 Sample seed: 42
Preparing MusicBrainz data for Neo4j...
[...]

📊 Integrity Score: 99.8% (✅ GOOD)
🔗 Total Relationships: 617,283
❌ Broken Relationships: 1,234

✅ Graph integrity validated successfully!
```

### 3. Custom Sampling with Validation

```bash
python utils/files_manager/csv_helper.py \
  --sample-percent 0.1 \
  --sample-seed 999 \
  --validate-sampling \
  --delimiter "," \
  --encoding "utf-8"
```

### 4. Selective Processing

```bash
# Only generate headers
python utils/files_manager/csv_helper.py \
  --skip-labels \
  --skip-relationships

# Only process relationships
python utils/files_manager/csv_helper.py \
  --skip-headers \
  --skip-labels \
  --mode testing
```

### 5. Large Dataset Processing

```bash
# Process with custom directories
python utils/files_manager/csv_helper.py \
  --mbdump /data/musicbrainz-20231101 \
  --headers-dir /tmp/neo4j/headers \
  --labeled-dir /tmp/neo4j/labeled \
  --relationships-dir /tmp/neo4j/relationships \
  --mode production
```

## Sampling Strategies

### Understanding Sampling

The tool uses **referential integrity sampling** to maintain graph consistency:

- **Node Sampling**: Randomly selects entities from each type
- **Relationship Filtering**: Only includes relationships where both endpoints exist
- **Integrity Validation**: Post-processing checks for broken links

### Recommended Configurations

| Use Case          | Sample % | Validation     | Notes                                |
| ----------------- | -------- | -------------- | ------------------------------------ |
| **Development**   | 50%      | ✅ Required    | Fast iteration, good for debugging   |
| **CI/CD Testing** | 25-50%   | ✅ Required    | Automated testing with consistency   |
| **Staging**       | 75-100%  | ✅ Recommended | Balance speed vs. representativeness |
| **Production**    | 100%     | ✅ Recommended | Complete dataset, full validation    |

### Sampling Best Practices

1. **Use Fixed Seeds**: For reproducible results
2. **Always Validate**: Check integrity after sampling
3. **Start Small**: Begin with 10-25% for initial testing
4. **Monitor Integrity**: Scores <95% indicate potential issues

## Validation Features

### What Gets Validated

The verification process performs comprehensive integrity checks:

- **Node Existence**: Verifies all referenced nodes exist
- **Relationship Validity**: Checks both endpoints of each relationship
- **Integrity Scoring**: Percentage of valid relationships
- **Detailed Reporting**: Breakdown by relationship type

### Validation Output Interpretation

#### ✅ GOOD Status (≥95% integrity)

```
📊 Integrity Score: 98.7% (✅ GOOD)
🔗 Total Relationships: 45,231
❌ Broken Relationships: 587
```

**Action**: Proceed normally, minor issues acceptable.

#### ⚠️ WARNING Status (80-95% integrity)

```
📊 Integrity Score: 87.3% (⚠️ WARNING)
🔗 Total Relationships: 45,231
❌ Broken Relationships: 5,823
```

**Action**: Investigate data sources or increase sample size.

#### ❌ CRITICAL Status (<80% integrity)

```
📊 Integrity Score: 65.4% (❌ CRITICAL)
🔗 Total Relationships: 45,231
❌ Broken Relationships: 15,823
```

**Action**: Stop and debug data pipeline.

## Troubleshooting

### Common Issues

#### 1. Missing Source Files

```
Error: Path must be a directory: mbdump
```

**Solution**: Ensure MusicBrainz TSV files are in the correct directory:

```bash
ls -la mbdump/
# Should contain: artist, recording, release, work, area, etc.
```

#### 2. Neo4j Connection Issues

```
Error: Unable to connect to Neo4j
```

**Solutions**:

- Check Neo4j is running: `sudo systemctl status neo4j`
- Verify credentials in `.env`
- Check firewall settings

#### 3. Memory Issues

```
MemoryError: Unable to allocate array
```

**Solutions**:

- Use sampling: Set `SAMPLE_PERCENT=50.0`
- Increase system memory
- Process in smaller batches

#### 4. Encoding Errors

```
UnicodeDecodeError: 'utf-8' codec can't decode
```

**Solutions**:

- Set correct encoding in `.env`: `ENCODING=latin-1`
- Check source file encoding

### Performance Optimization

#### For Large Datasets

```bash
# Use testing mode
SAMPLE_PERCENT=50.0

# Skip unnecessary steps
SKIP_HEADERS=true
```

#### For Fast Iteration

```bash
# Small sample with validation
SAMPLE_PERCENT=5.0
VERIFY=true
```

## Advanced Usage

### Custom Configuration

```bash
# Advanced .env configuration
TSV_DIR=/data/musicbrainz-2024
HEADERS_DIR=/tmp/headers
LABELED_DIR=/tmp/labeled
RELATIONSHIPS_DIR=/tmp/relationships
SAMPLE_PERCENT=75.0
SAMPLE_SEED=999
DELIMITER=\t
ENCODING=utf-8
DB_NAME=musicbrainz-custom.db
VERIFY=true
NEO4J_BIN_PATH=/opt/neo4j/bin
JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### Integration Scripts

```bash
#!/bin/bash
# automated_pipeline.sh

echo "Starting automated pipeline..."

# Set environment
export SAMPLE_PERCENT=100
export VERIFY=true

# Run build
python cli.py build

# Check result
if [ $? -eq 0 ]; then
    echo "✅ Pipeline successful"
    # Send notification or continue
else
    echo "❌ Pipeline failed"
    exit 1
fi
```

### Monitoring

```bash
# Log output
python cli.py build 2>&1 | tee build_$(date +%Y%m%d_%H%M%S).log

# Check results
grep "🎉 Full build process completed" *.log
grep "Integrity Score" *.log
```

## File Structure

After successful processing:

```
project/
├── .env                    # Configuration file
├── out_csv/               # Converted CSV files
├── neo4j_headers/         # Neo4j header files
│   ├── artist_header.csv
│   └── ...
├── labeled/               # Labeled node data
│   ├── labeled_artist.csv
│   └── ...
└── relationships/         # Relationship data
    ├── artist_recording_relationships.csv
    ├── artist_release_relationships.csv
    └── ...
```

## Support

For issues or questions:

- Check the CLI output for specific error details
- Review the [main README](../README.md) for architecture overview
- Open an issue in the project repository

## Version History

- **v1.0**: Basic CLI commands
- **v1.1**: Added sampling support
- **v1.2**: Added full build automation
- **v1.3**: Enhanced with Typer and configuration files
