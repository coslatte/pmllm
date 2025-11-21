from pathlib import Path
import typer
from dotenv import load_dotenv
import os
from typing import Optional, cast
from utils.files_manager.converter import Converter
from utils.files_manager.csv_helper import run_pipeline
from db.neo4j.neo4j_importer import run_bulk_import, run_verification_queries

app = typer.Typer()


def handle_convert(src: Path, out_dir: Path) -> int:
    """
    Convert TSV files to CSV format.
    """
    if not src.is_dir():
        raise ValueError(f"Path must be a directory: {src}")

    out_dir.mkdir(parents=True, exist_ok=True)
    converted = Converter.convert_tsvs_in_dir(src, out_dir)
    return converted


def handle_prepare(
    core_dir: Path,
    derived_dir: Path,
    output_dir: Path,
    delimiter: str,
    encoding: str,
    skip_headers: bool,
    skip_labels: bool,
    skip_relationships: bool,
    sample_fraction: float,
    sample_seed: int,
):
    """
    Prepare MusicBrainz data for Neo4j.
    """
    run_pipeline(
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


def handle_import_neo4j(
    headers_dir: Path,
    labeled_dir: Path,
    relationships_dir: Path,
    db_name: str,
    delimiter: str,
    array_delimiter: str,
    skip_bad_relationships: bool,
    multiline_fields: bool,
    verify: bool,
    user: str,
    password: Optional[str],
    host: str,
    port: int,
    neo4j_bin_path: Optional[Path] = None,
    java_home: Optional[Path] = None,
    legacy_import: bool = False,
):
    """
    Run Neo4j bulk import.
    """
    run_bulk_import(
        headers_dir=headers_dir,
        labeled_dir=labeled_dir,
        relationships_dir=relationships_dir,
        db_name=db_name,
        delimiter=delimiter,
        array_delimiter=array_delimiter,
        skip_bad_relationships=skip_bad_relationships,
        multiline_fields=multiline_fields,
        neo4j_bin_path=neo4j_bin_path,
        java_home=java_home,
        legacy_import=legacy_import,
    )

    if verify:
        if not password:
            password = os.getenv("NEO4J_PASSWORD")
        if not password:
            typer.echo("Warning: No password provided for verification. Set NEO4J_PASSWORD or provide in config.", err=True)
            return
        
        run_verification_queries(
            user=user,
            password=password,
            host=host,
            port=port,
        )


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
        typer.secho(f"✓ Converted {converted} file(s) to: {out_dir.resolve()}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("prepare-neo4j")
def prepare_neo4j(
    core_dir: str = typer.Option("music_metadata", help="Directory with core MusicBrainz TSV files"),
    derived_dir: str = typer.Option("music_derived_metadata", help="Directory with derived MusicBrainz TSV files"),
    output_dir: str = typer.Option("output", help="Base output directory (creates core/ and derived/ subdirs)"),
    sample_percent: float = typer.Option(100.0, help="Percent of rows to keep when generating CSVs"),
    sample_seed: int = typer.Option(42, help="Random seed controlling which rows are kept during sampling"),
    delimiter: str = typer.Option("\t", help="Delimiter used by input files"),
    encoding: str = typer.Option("utf-8", help="Encoding used when reading and writing files"),
    skip_headers: bool = typer.Option(False, help="Skip header generation"),
    skip_labels: bool = typer.Option(False, help="Skip creation of labeled files"),
    skip_relationships: bool = typer.Option(False, help="Skip relationship generation"),
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
        typer.secho("✓ Preparation completed!", fg=typer.colors.GREEN)
        typer.echo("\nGenerated files:")
        if not skip_headers:
            typer.echo(f"  - {Path(output_dir).resolve()}/core/headers/ (core header files)")
        if not skip_labels:
            typer.echo(f"  - {Path(output_dir).resolve()}/core/labeled/ (core labeled data)")
            typer.echo(f"  - {Path(output_dir).resolve()}/derived/labeled/ (derived labeled data)")
        if not skip_relationships:
            typer.echo(f"  - {Path(output_dir).resolve()}/core/relationships/ (core relationship files)")
            typer.echo(f"  - {Path(output_dir).resolve()}/derived/relationships/ (derived relationship files)")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("import-neo4j")
def import_neo4j(
    output_dir: str = typer.Option("output", help="Base output directory (reads from core/ subdirs)"),
    db_name: str = typer.Option("musicbrainz.db", help="Target Neo4j database name for bulk import"),
    delimiter: str = typer.Option("\t", help="Field delimiter used in CSV files"),
    array_delimiter: str = typer.Option(";", help="Array delimiter used in CSV fields"),
    allow_bad_relationships: bool = typer.Option(False, help="Do not skip bad relationships"),
    multiline_fields: bool = typer.Option(True, help="Treat fields as multiline"),
    verify: bool = typer.Option(False, help="Run simple verification Cypher queries after import"),
    user: str = typer.Option("neo4j", help="Neo4j username for verification queries"),
    password: str = typer.Option(None, help="Neo4j password for verification queries"),
    host: str = typer.Option("localhost", help="Neo4j host for verification queries"),
    port: int = typer.Option(7687, help="Neo4j Bolt port for verification queries"),
    neo4j_bin_path: str = typer.Option(None, help="Path to Neo4j bin directory"),
    java_home: str = typer.Option(None, help="Path to Java installation"),
    legacy_import: bool = typer.Option(False, help="Use legacy neo4j-admin import"),
):
    """
    Run Neo4j bulk import using generated CSV headers and data.
    """
    try:
        neo4j_bin = Path(neo4j_bin_path) if neo4j_bin_path else None  # type: ignore
        java_home_path = Path(java_home) if java_home else None  # type: ignore
        typer.secho("Running Neo4j bulk import...", fg=typer.colors.BLUE)
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
        typer.secho("✓ Neo4j bulk import completed.", fg=typer.colors.GREEN)
        if verify:
            typer.secho("✓ Verification queries completed.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
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
        typer.secho(f"Loaded config from: {config}", fg=typer.colors.CYAN)

        # Extract config values with defaults
        core_dir = Path(os.getenv("TSV_CORE_DIR", "music_metadata"))
        derived_dir = Path(os.getenv("TSV_DERIVED_DIR", "music_derived_metadata"))
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        csv_out_dir = Path(os.getenv("CSV_OUT_DIR", "out_csv"))
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
        allow_bad_relationships = os.getenv("ALLOW_BAD_RELATIONSHIPS", "false").lower() == "true"
        multiline_fields = os.getenv("MULTILINE_FIELDS", "true").lower() == "true"
        verify = os.getenv("VERIFY", "true").lower() == "true"
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        neo4j_host = os.getenv("NEO4J_HOST", "localhost")
        neo4j_port = int(os.getenv("NEO4J_PORT", "7687"))
        neo4j_bin_path = Path(cast(str, os.getenv("NEO4J_BIN_PATH"))) if os.getenv("NEO4J_BIN_PATH") else None
        java_home = Path(cast(str, os.getenv("JAVA_HOME"))) if os.getenv("JAVA_HOME") else None
        legacy_import = os.getenv("LEGACY_IMPORT", "false").lower() == "true"

        sample_fraction = max(0.0, min(sample_percent, 100.0)) / 100.0

        typer.secho("Starting full build process...", fg=typer.colors.BLUE, bold=True)

        # Note: TSV conversion should be done separately for core and derived directories
        # using: python cli.py convert <directory> --out <csv_output_dir>
        typer.secho("Note: Ensure TSV files are already converted to CSV if needed", fg=typer.colors.CYAN)

        # Step 1: Prepare headers and data
        typer.secho("\nStep 1: Preparing headers and data for Neo4j", fg=typer.colors.YELLOW, bold=True)
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
        typer.secho("✓ Preparation completed!", fg=typer.colors.GREEN)
        typer.echo("Generated files:")
        if not skip_headers:
            typer.echo(f"  - {output_dir.resolve()}/core/headers/ (core header files)")
        if not skip_labels:
            typer.echo(f"  - {output_dir.resolve()}/core/labeled/ (core labeled data)")
            typer.echo(f"  - {output_dir.resolve()}/derived/labeled/ (derived labeled data)")
        if not skip_relationships:
            typer.echo(f"  - {output_dir.resolve()}/core/relationships/ (core relationship files)")
            typer.echo(f"  - {output_dir.resolve()}/derived/relationships/ (derived relationship files)")

        # Step 2: Import to Neo4j
        typer.secho("\nStep 2: Importing to Neo4j", fg=typer.colors.YELLOW, bold=True)
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
        typer.secho("✓ Neo4j import completed.", fg=typer.colors.GREEN)
        if verify:
            typer.secho("✓ Verification completed.", fg=typer.colors.GREEN)

        typer.secho("\n🎉 Full build process completed successfully!", fg=typer.colors.GREEN, bold=True)

    except Exception as e:
        typer.secho(f"Error during build: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
