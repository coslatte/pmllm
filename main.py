from dotenv import load_dotenv
import os
from pathlib import Path
import typer
from typing import cast
from utils.helpers.convert_handler import handle_convert
from utils.helpers.prepare_handler import handle_prepare
from utils.helpers.import_handler import handle_import_neo4j
from db.vector.build_vector_db import populate
from utils.constants.cli_colors import SUCCESS, ERROR, INFO

# Load environment variables from .env file
load_dotenv(override=True)
print("Loaded NEO4J_PASSWORD:", repr(os.getenv("NEO4J_PASSWORD")))

app = typer.Typer()


@app.command("convert")
def convert(
    path: str = typer.Argument(..., help="Path to a directory containing .tsv files"),
    out: str = typer.Option("out_csv", help="Output directory for generated CSV files"),
):
    """
    Convert TSV files to CSV format (extracts tars, processes all TSVs found).
    """
    try:
        src = Path(path)
        out_dir = Path(out)
        with typer.progressbar(length=1, label="Converting TSV to CSV") as progress:
            converted = handle_convert(src, out_dir)
            progress.update(1)
        typer.secho(
            f"✓ Converted {converted} file(s) to: {out_dir.resolve()}", fg=SUCCESS
        )
    except Exception as e:
        typer.secho(f"Error: {e}", fg=ERROR, err=True)
        raise typer.Exit(1)


@app.command("prepare-neo4j")
def prepare_neo4j(
    core_dir: str = typer.Option(
        os.getenv("TSV_CORE_DIR", "music_metadata"), help="Directory with core MusicBrainz TSV files"
    ),
    derived_dir: str = typer.Option(
        os.getenv("TSV_DERIVED_DIR", "music_derived_metadata"), help="Directory with derived MusicBrainz TSV files"
    ),
    output_dir: str = typer.Option(
        os.getenv("OUTPUT_DIR", "output"), help="Base output directory (creates core/ and derived/ subdirs)"
    ),
    sample_percent: float = typer.Option(
        float(os.getenv("SAMPLE_PERCENT", "100.0")), help="Percent of rows to keep when generating CSVs"
    ),
    sample_seed: int = typer.Option(
        int(os.getenv("SAMPLE_SEED", "42")), help="Random seed controlling which rows are kept during sampling"
    ),
    delimiter: str = typer.Option(
        os.getenv("DELIMITER", "\t"), help="Delimiter used by input files"
    ),
    encoding: str = typer.Option(
        os.getenv("ENCODING", "utf-8"), help="Encoding used when reading and writing files"
    ),
    skip_headers: bool = typer.Option(
        os.getenv("SKIP_HEADERS", "false").lower() == "true", help="Skip header generation"
    ),
    skip_labels: bool = typer.Option(
        os.getenv("SKIP_LABELS", "false").lower() == "true", help="Skip creation of labeled files"
    ),
    skip_relationships: bool = typer.Option(
        os.getenv("SKIP_RELATIONSHIPS", "false").lower() == "true", help="Skip relationship generation"
    ),
):
    """
    Generate headers, labels, and relationships for Neo4j.
    """
    try:
        sample_fraction = max(0.0, min(sample_percent, 100.0)) / 100.0
        handle_prepare(
            core_dir=Path(core_dir),
            derived_dir=Path(derived_dir),
            output_dir=Path(output_dir),
            delimiter=delimiter,
            encoding=encoding,
            skip_headers=skip_headers,
            skip_labels=skip_labels,
            skip_relationships=skip_relationships,
            sample_fraction=sample_fraction,
            sample_seed=sample_seed,
        )
        typer.secho("✓ Preparation completed!", fg=SUCCESS)
        typer.echo("\nGenerated files:")
        if not skip_headers:
            typer.echo(
                f"  - {Path(output_dir).resolve()}/core/headers/ (core header files)"
            )
        if not skip_labels:
            typer.echo(
                f"  - {Path(output_dir).resolve()}/core/labeled/ (core labeled data)"
            )
            typer.echo(
                f"  - {Path(output_dir).resolve()}/derived/labeled/ (derived labeled data)"
            )
        if not skip_relationships:
            typer.echo(
                f"  - {Path(output_dir).resolve()}/core/relationships/ (core relationship files)"
            )
            typer.echo(
                f"  - {Path(output_dir).resolve()}/derived/relationships/ (derived relationship files)"
            )
    except Exception as e:
        typer.secho(f"Error: {e}", fg=ERROR, err=True)
        raise typer.Exit(1)


@app.command("import-neo4j")
def import_neo4j(
    output_dir: str = typer.Option(
        os.getenv("OUTPUT_DIR", "output"), help="Base output directory (reads from core/ subdirs)"
    ),
    db_name: str = typer.Option(
        os.getenv("DB_NAME", "musicbrainz.db"), help="Target Neo4j database name for bulk import"
    ),
    delimiter: str = typer.Option(
        os.getenv("DELIMITER", "\t"), help="Field delimiter used in CSV files"
    ),
    array_delimiter: str = typer.Option(
        os.getenv("ARRAY_DELIMITER", ";"), help="Array delimiter used in CSV fields"
    ),
    allow_bad_relationships: bool = typer.Option(
        os.getenv("ALLOW_BAD_RELATIONSHIPS", "false").lower() == "true", help="Do not skip bad relationships"
    ),
    multiline_fields: bool = typer.Option(
        os.getenv("MULTILINE_FIELDS", "true").lower() == "true", help="Treat fields as multiline"
    ),
    verify: bool = typer.Option(
        os.getenv("VERIFY", "false").lower() == "true", help="Run simple verification Cypher queries after import"
    ),
    user: str = typer.Option(
        os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username for verification queries"
    ),
    password: str = typer.Option(
        os.getenv("NEO4J_PASSWORD", ""), help="Neo4j password for verification queries"
    ),
    host: str = typer.Option(
        os.getenv("NEO4J_HOST", "localhost"), help="Neo4j host for verification queries"
    ),
    port: int = typer.Option(
        int(os.getenv("NEO4J_PORT", "7687")), help="Neo4j Bolt port for verification queries"
    ),
    neo4j_bin_path: str = typer.Option(
        os.getenv("NEO4J_BIN_PATH", None), help="Path to Neo4j bin directory"
    ),
    java_home: str = typer.Option(
        os.getenv("JAVA_HOME", None), help="Path to Java installation"
    ),
    legacy_import: bool = typer.Option(
        os.getenv("LEGACY_IMPORT", "false").lower() == "true", help="Use legacy neo4j-admin import"
    ),
):
    """
    Run Neo4j bulk import using generated CSV headers and data.
    """
    try:
        neo4j_bin = Path(neo4j_bin_path) if neo4j_bin_path else None  # type: ignore
        java_home_path = Path(java_home) if java_home else None  # type: ignore
        typer.secho("Running Neo4j bulk import...", fg=INFO)
        handle_import_neo4j(
            headers_dir=Path(output_dir) / "core" / "headers",
            labeled_dir=Path(output_dir) / "core" / "labeled",
            relationships_dir=Path(output_dir) / "core" / "relationships",
            db_name=db_name,
            delimiter=delimiter,
            array_delimiter=array_delimiter,
            skip_bad_relationships=not allow_bad_relationships,
            multiline_fields=multiline_fields,
            verify=verify,
            user=user,
            password=password,
            host=host,
            port=port,
            neo4j_bin_path=neo4j_bin,
            java_home=java_home_path,
            legacy_import=legacy_import,
        )
        typer.secho("✓ Neo4j bulk import completed.", fg=SUCCESS)
        if verify:
            typer.secho("✓ Verification queries completed.", fg=SUCCESS)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=ERROR, err=True)
        raise typer.Exit(1)


@app.command("build")
def build(
    config: str = typer.Option(".env", help="Path to config file (.env format)"),
):
    """
    Run the full build process: convert TSV to CSV, prepare headers/data, and import to Neo4j.
    Reads configuration from the specified .env file.

    Now includes support for derived MusicBrainz data (labels, places, events, genres, etc.)
    when PROCESS_* options are enabled in the config file.
    """
    try:
        load_dotenv(config)
        typer.secho(f"Loaded config from: {config}", fg=INFO)

        # Extract config values with defaults
        core_dir = Path(os.getenv("TSV_CORE_DIR", "music_metadata"))
        derived_dir = Path(os.getenv("TSV_DERIVED_DIR", "music_derived_metadata"))
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        sample_percent = float(os.getenv("SAMPLE_PERCENT", "100.0"))
        sample_seed = int(os.getenv("SAMPLE_SEED", "42"))
        delimiter = os.getenv("DELIMITER", "\t")
        # Handle escape sequences in delimiter
        if delimiter == "\\t":
            delimiter = "\t"
        encoding = os.getenv("ENCODING", "utf-8")
        skip_headers = os.getenv("SKIP_HEADERS", "false").lower() == "true"
        skip_labels = os.getenv("SKIP_LABELS", "false").lower() == "true"
        skip_relationships = os.getenv("SKIP_RELATIONSHIPS", "false").lower() == "true"
        db_name = os.getenv("DB_NAME", "musicbrainz.db")
        array_delimiter = os.getenv("ARRAY_DELIMITER", ";")
        allow_bad_relationships = (
            os.getenv("ALLOW_BAD_RELATIONSHIPS", "false").lower() == "true"
        )
        multiline_fields = os.getenv("MULTILINE_FIELDS", "true").lower() == "true"
        verify = os.getenv("VERIFY", "true").lower() == "true"
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        neo4j_host = os.getenv("NEO4J_HOST", "localhost")
        neo4j_port = int(os.getenv("NEO4J_PORT", "7687"))
        neo4j_bin_path = (
            Path(cast(str, os.getenv("NEO4J_BIN_PATH")))
            if os.getenv("NEO4J_BIN_PATH")
            else None
        )
        java_home = (
            Path(cast(str, os.getenv("JAVA_HOME"))) if os.getenv("JAVA_HOME") else None
        )
        legacy_import = os.getenv("LEGACY_IMPORT", "false").lower() == "true"

        sample_fraction = max(0.0, min(sample_percent, 100.0)) / 100.0

        typer.secho("Starting full build process...", fg=INFO, bold=True)

        # Note: TSV conversion should be done separately for core and derived directories
        # using: python cli.py convert <directory> --out <csv_output_dir>
        typer.secho(
            "Note: Ensure TSV files are already converted to CSV if needed", fg=INFO
        )

        # Step 1: Prepare headers and data
        typer.secho(
            "\nStep 1: Preparing headers and data for Neo4j", fg=INFO, bold=True
        )
        handle_prepare(
            core_dir=core_dir,
            derived_dir=derived_dir,
            output_dir=output_dir,
            delimiter=delimiter,
            encoding=encoding,
            skip_headers=skip_headers,
            skip_labels=skip_labels,
            skip_relationships=skip_relationships,
            sample_fraction=sample_fraction,
            sample_seed=sample_seed,
        )
        typer.secho("✓ Preparation completed!", fg=SUCCESS)
        typer.echo("Generated files:")
        if not skip_headers:
            typer.echo(f"  - {output_dir.resolve()}/core/headers/ (core header files)")
        if not skip_labels:
            typer.echo(f"  - {output_dir.resolve()}/core/labeled/ (core labeled data)")
            typer.echo(
                f"  - {output_dir.resolve()}/derived/labeled/ (derived labeled data)"
            )
        if not skip_relationships:
            typer.echo(
                f"  - {output_dir.resolve()}/core/relationships/ (core relationship files)"
            )
            typer.echo(
                f"  - {output_dir.resolve()}/derived/relationships/ (derived relationship files)"
            )

        # Step 2: Import to Neo4j
        typer.secho("\nStep 2: Importing to Neo4j", fg=INFO, bold=True)
        handle_import_neo4j(
            headers_dir=output_dir / "core" / "headers",
            labeled_dir=output_dir / "core" / "labeled",
            relationships_dir=output_dir / "core" / "relationships",
            db_name=db_name,
            delimiter=delimiter,
            array_delimiter=array_delimiter,
            skip_bad_relationships=not allow_bad_relationships,
            multiline_fields=multiline_fields,
            verify=verify,
            user=neo4j_user,
            password=neo4j_password,
            host=neo4j_host,
            port=neo4j_port,
            neo4j_bin_path=neo4j_bin_path,
            java_home=java_home,
            legacy_import=legacy_import,
        )
        typer.secho("✓ Neo4j import completed.", fg=SUCCESS)
        if verify:
            typer.secho("✓ Verification completed.", fg=SUCCESS)

        typer.secho(
            "\n🎉 Full build process completed successfully!", fg=SUCCESS, bold=True
        )

    except Exception as e:
        typer.secho(f"Error during build: {e}", fg=ERROR, err=True)
        raise typer.Exit(1)


@app.command("build-vector")
def build_vector(
    labels: str = typer.Option(
        "Artist,Recording,Release,Tag,ArtistCredit",
        help="Comma-separated list of Neo4j node labels to process",
    ),
):
    """
    Build the vector database by generating embeddings for nodes from Neo4j and storing in Milvus.
    """
    try:
        load_dotenv()
        label_list = [label.strip() for label in labels.split(",")]
        typer.secho(f"Building vector DB for labels: {label_list}", fg=INFO)
        populate(label_list)
        typer.secho("✓ Vector DB build completed!", fg=SUCCESS)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=ERROR, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
