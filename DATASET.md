# Dataset Documentation

## MusicBrainz Dataset

The system uses a fragmented MusicBrainz dataset containing music metadata and relationships.

### Source

- **Original Source**: MusicBrainz (musicbrainz.org)
- **Format**: PostgreSQL dumps + Neo4j exports
- **Scope**: Music metadata including artists, recordings, releases, works, and relationships

### Data Structure

#### Core Entities

- **Artists**: Biographical data, origins, genres
- **Recordings**: Individual tracks with metadata
- **Releases**: Albums and singles
- **Works**: Musical compositions
- **Areas**: Geographic locations
- **Release Groups**: Logical groupings
- **Tags**: Genre and category labels

#### Derived Entities

- **Labels**: Record companies
- **Mediums**: Physical formats (CD, Vinyl, Digital)
- **Tracks**: Individual tracks in releases
- **Places**: Recording venues and studios
- **Events**: Concerts and festivals
- **Genres**: Music genres
- **Instruments**: Musical instruments
- **Series**: Album/artist series
- **URLs**: External links

#### Relationships

- Artist-Recording (performed on)
- Artist-Release (released)
- Recording-Work (belongs to)
- Geographic associations
- Genre classifications
- Industry relationships

### Processing Pipeline

1. **TSV to CSV Conversion**: Raw MusicBrainz dumps to CSV format
2. **Data Labeling**: Add entity type labels for Neo4j import
3. **Relationship Generation**: Create relationship files for graph connections
4. **Sampling**: Optional data reduction for testing/development
5. **Neo4j Import**: Bulk import to graph database
6. **Vector Embedding**: Generate embeddings for RAG retrieval

### Configuration

Data processing is controlled via environment variables in `.env`:

- `SAMPLE_PERCENT`: Data sampling percentage
- `PROCESS_*`: Enable/disable derived data types
- `TSV_CORE_DIR`: Core data location
- `TSV_DERIVED_DIR`: Derived data location

### Quality Assurance

- Schema validation for all entity types
- Relationship integrity checks
- Sampling compatibility
- Optimized for music recommendation use cases

### Usage in RAG

- **Vector Search**: Semantic similarity over entity descriptions
- **Graph Context**: Structured relationships from Neo4j
- **Generation**: Contextual answers using Gemma 3 LLM
