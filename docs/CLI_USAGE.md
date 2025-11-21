# MusicBrainz Data Preparation CLI Usage Guide

This guide provides comprehensive instructions for using the `pmllm-csv-helper` CLI tool to prepare MusicBrainz data for Neo4j import.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Usage Examples](#usage-examples)
- [Sampling Strategies](#sampling-strategies)
- [Validation Features](#validation-features)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The `pmllm-csv-helper` tool transforms raw MusicBrainz TSV files into Neo4j-compatible CSV format with proper headers and relationships. It supports:

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

### Basic Usage (Production Mode)

```bash
# Prepare full dataset for production
python utils/file_manager/csv_helper.py \
  --mode production \
  --validate-sampling
```

### Development/Testing Mode

```bash
# Prepare 50% sample for faster development
python utils/file_manager/csv_helper.py \
  --mode testing \
  --validate-sampling
```

### Custom Sampling

```bash
# Use 25% sample with custom seed
python utils/file_manager/csv_helper.py \
  --sample-percent 0.25 \
  --sample-seed 12345 \
  --validate-sampling
```

## Command Reference

### Main Command

```bash
python utils/file_manager/csv_helper.py [OPTIONS]
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
python utils/file_manager/csv_helper.py \
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
python utils/file_manager/csv_helper.py \
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
python utils/file_manager/csv_helper.py \
  --sample-percent 0.1 \
  --sample-seed 999 \
  --validate-sampling \
  --delimiter "," \
  --encoding "utf-8"
```

### 4. Selective Processing

```bash
# Only generate headers
python utils/file_manager/csv_helper.py \
  --skip-labels \
  --skip-relationships

# Only process relationships
python utils/file_manager/csv_helper.py \
  --skip-headers \
  --skip-labels \
  --mode testing
```

### 5. Large Dataset Processing

```bash
# Process with custom directories
python utils/file_manager/csv_helper.py \
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

| Use Case          | Mode         | Sample % | Validation     | Notes                                |
| ----------------- | ------------ | -------- | -------------- | ------------------------------------ |
| **Development**   | `testing`    | 50%      | ✅ Required    | Fast iteration, good for debugging   |
| **CI/CD Testing** | `testing`    | 50%      | ✅ Required    | Automated testing with consistency   |
| **Staging**       | Custom       | 25-75%   | ✅ Required    | Balance speed vs. representativeness |
| **Production**    | `production` | 100%     | ✅ Recommended | Complete dataset, full validation    |

### Sampling Best Practices

1. **Use Fixed Seeds**: `--sample-seed 42` for reproducible results
2. **Always Validate**: `--validate-sampling` to catch integrity issues
3. **Start Small**: Begin with 10-25% for initial testing
4. **Monitor Integrity**: Scores <95% indicate potential issues

## Validation Features

### What Gets Validated

The `--validate-sampling` flag performs comprehensive integrity checks:

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

### Validation Details

The validation provides:

- **Node counts** by type
- **Relationship statistics** with broken/total counts
- **Examples of broken relationships** (first 10)
- **Connectivity metrics** for each node type

## Troubleshooting

### Common Issues

#### 1. Missing Source Files

```
FileNotFoundError: Required file not found: mbdump/artist
```

**Solution**: Ensure MusicBrainz TSV files are in the correct directory:

```bash
ls -la mbdump/
# Should contain: artist, recording, release, work, area, etc.
```

#### 2. Low Integrity Scores

```
⚠️ WARNING: Low integrity score detected!
```

**Solutions**:

- Increase sample percentage: `--sample-percent 0.75`
- Check data source integrity
- Use different random seed: `--sample-seed 123`

#### 3. Memory Issues with Large Datasets

```
MemoryError: Unable to allocate array
```

**Solutions**:

- Use sampling: `--mode testing`
- Process in smaller batches
- Increase system memory

#### 4. Encoding Errors

```
UnicodeDecodeError: 'utf-8' codec can't decode
```

**Solutions**:

- Specify correct encoding: `--encoding latin-1`
- Check source file encoding
- Clean problematic characters

### Performance Optimization

#### For Large Datasets

```bash
# Use testing mode for development
python utils/file_manager/csv_helper.py --mode testing

# Skip unnecessary steps
python utils/file_manager/csv_helper.py \
  --skip-headers \
  --mode testing
```

#### For Fast Iteration

```bash
# Small sample with validation
python utils/file_manager/csv_helper.py \
  --sample-percent 0.05 \
  --validate-sampling
```

## Advanced Usage

### Custom Data Pipeline

```bash
# Multi-step processing
python utils/file_manager/csv_helper.py --skip-labels --skip-relationships
python utils/file_manager/csv_helper.py --skip-headers --skip-relationships
python utils/file_manager/csv_helper.py --skip-headers --skip-labels
```

### Integration with Neo4j Import

```bash
# Prepare data
python utils/file_manager/csv_helper.py --mode production

# Import to Neo4j
python cli.py import-neo4j \
  --headers-dir neo4j_headers \
  --labeled-dir labeled \
  --relationships-dir relationships \
  --db-name musicbrainz.db
```

### Automated Processing Scripts

```bash
#!/bin/bash
# production_pipeline.sh

echo "Starting production pipeline..."

# Prepare data
python utils/file_manager/csv_helper.py \
  --mode production \
  --validate-sampling \
  --mbdump /data/musicbrainz

# Check validation result
if [ $? -eq 0 ]; then
    echo "✅ Data preparation successful"
    # Proceed with Neo4j import
else
    echo "❌ Data preparation failed"
    exit 1
fi
```

### Monitoring and Logging

```bash
# Redirect output for logging
python utils/file_manager/csv_helper.py --mode testing 2>&1 | tee pipeline.log

# Check results
grep "Integrity Score" pipeline.log
grep "Preparation completed" pipeline.log
```

## File Structure

After successful processing, you'll have:

```
project/
├── neo4j_headers/           # Neo4j header files
│   ├── artist_header.csv
│   ├── recording_header.csv
│   └── ...
├── labeled/                 # Labeled node data
│   ├── labeled_artist.csv
│   ├── labeled_recording.csv
│   └── ...
└── relationships/           # Relationship data
    ├── artist_recording_relationships.csv
    ├── artist_release_relationships.csv
    └── ...
```

## Support

For issues or questions:

- Check the validation output for specific error details
- Review the [main README](../README.md) for architecture overview
- Open an issue in the project repository

## Version History

- **v1.0**: Basic CSV preparation functionality
- **v1.1**: Added sampling support
- **v1.2**: Added graph integrity validation
- **v1.3**: Added testing/production modes</content>
  <parameter name="filePath">d:\Coding\Projects\college\pmllm\docs\CLI_USAGE.md
