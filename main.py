import os
import socket
import time
from pathlib import Path
from typing import cast

import typer
from dotenv import load_dotenv

from db.vector.build_vector_db import populate
from utils.cli_helpers import (
    apply_demo_overrides,
    has_generated_files,
    print_preflight_summary,
    split_labels_from_env,
    warn_on_blank_env_vars,
)
from utils.constants import (
    CRITICAL_ENV_VARS,
    DEFAULT_VECTOR_LABELS,
    ERROR,
    INFO,
    SUCCESS,
)
from utils.helpers.convert_handler import handle_convert
from utils.helpers.desktop_bundle_handler import create_desktop_bundle
from utils.helpers.import_handler import handle_import_neo4j
from utils.helpers.prepare_handler import handle_prepare

# Load environment variables from .env file immediately
load_dotenv(override=True)


app = typer.Typer()


def _wait_for_bolt(host: str, port: int, timeout: float = 120.0) -> bool:
    """Poll until the Neo4j Bolt port is reachable."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except OSError:
            time.sleep(2)
    return False


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
            f"✓ Converted {converted} file(s) to: {out_dir.resolve()}",
            fg=typer.colors.GREEN,
        )
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("prepare-neo4j")
def prepare_neo4j(
    core_dir: str = typer.Option(
        os.getenv("TSV_CORE_DIR", "music_metadata"),
        help="Directory with core MusicBrainz TSV files",
    ),
    derived_dir: str = typer.Option(
        os.getenv("TSV_DERIVED_DIR", "music_derived_metadata"),
        help="Directory with derived MusicBrainz TSV files",
    ),
    output_dir: str = typer.Option(
        os.getenv("OUTPUT_DIR", "output"),
        help="Base output directory (creates core/ and derived/ subdirs)",
    ),
    sample_percent: float = typer.Option(
        float(os.getenv("SAMPLE_PERCENT", "100.0")),
        help="Percent of rows to keep when generating CSVs",
    ),
    sample_seed: int = typer.Option(
        int(os.getenv("SAMPLE_SEED", "42")),
        help="Random seed controlling which rows are kept during sampling",
    ),
    delimiter: str = typer.Option(
        os.getenv("DELIMITER", "\t"), help="Delimiter used by input files"
    ),
    encoding: str = typer.Option(
        os.getenv("ENCODING", "utf-8"),
        help="Encoding used when reading and writing files",
    ),
    skip_headers: bool = typer.Option(
        os.getenv("SKIP_HEADERS", "false").lower() == "true",
        help="Skip header generation",
    ),
    skip_labels: bool = typer.Option(
        os.getenv("SKIP_LABELS", "false").lower() == "true",
        help="Skip creation of labeled files",
    ),
    skip_relationships: bool = typer.Option(
        os.getenv("SKIP_RELATIONSHIPS", "false").lower() == "true",
        help="Skip relationship generation",
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
        typer.secho("✓ Preparation completed!", fg=typer.colors.GREEN)
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
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("prepare-desktop")
def prepare_desktop(
    output_dir: str = typer.Option(
        os.getenv("OUTPUT_DIR", "output"),
        help="Base output directory produced by `prepare-neo4j`",
    ),
    bundle_dir: str = typer.Option(
        None,
        help="Destination directory for the Neo4j Desktop bundle (defaults to OUTPUT_DIR/neo4j_desktop)",
    ),
    delimiter: str = typer.Option(
        os.getenv("DELIMITER", "\t"),
        help="Delimiter used in the CSV files (must match the prepare step)",
    ),
    encoding: str = typer.Option(
        os.getenv("ENCODING", "utf-8"),
        help="Encoding used in the CSV files",
    ),
    include_derived_nodes: bool = typer.Option(
        True,
        help="Include derived labeled nodes (labels, mediums, etc.) if they exist",
    ),
    include_extended_relationships: bool = typer.Option(
        True,
        help="Include extended relationship files generated under derived/relationships",
    ),
):
    """Create header+data CSVs that Neo4j Desktop can import via drag-and-drop."""

    try:
        summary = create_desktop_bundle(
            output_dir=Path(output_dir),
            bundle_dir=Path(bundle_dir) if bundle_dir else None,
            delimiter="\t" if delimiter == "\\t" else delimiter,
            encoding=encoding,
            include_derived_nodes=include_derived_nodes,
            include_extended_relationships=include_extended_relationships,
        )

        typer.secho("✓ Neo4j Desktop bundle created", fg=typer.colors.GREEN)
        typer.echo(f"Nodes written: {len(summary['nodes'])}")
        typer.echo(f"Relationships written: {len(summary['relationships'])}")
        typer.echo(f"Bundle directory: {summary['nodes'][0].parent.parent}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("import-neo4j")
def import_neo4j(
    output_dir: str = typer.Option(
        os.getenv("OUTPUT_DIR", "output"),
        help="Base output directory (reads from core/ subdirs)",
    ),
    db_name: str = typer.Option(
        os.getenv("DB_NAME", "musicbrainz.db"),
        help="Target Neo4j database name for bulk import",
    ),
    delimiter: str = typer.Option(
        os.getenv("DELIMITER", "\t"), help="Field delimiter used in CSV files"
    ),
    array_delimiter: str = typer.Option(
        os.getenv("ARRAY_DELIMITER", ";"), help="Array delimiter used in CSV fields"
    ),
    allow_bad_relationships: bool = typer.Option(
        os.getenv("ALLOW_BAD_RELATIONSHIPS", "false").lower() == "true",
        help="Do not skip bad relationships",
    ),
    multiline_fields: bool = typer.Option(
        os.getenv("MULTILINE_FIELDS", "true").lower() == "true",
        help="Treat fields as multiline",
    ),
    verify: bool = typer.Option(
        os.getenv("VERIFY", "false").lower() == "true",
        help="Run simple verification Cypher queries after import",
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
        int(os.getenv("NEO4J_PORT", "7687")),
        help="Neo4j Bolt port for verification queries",
    ),
    neo4j_bin_path: str = typer.Option(
        os.getenv("NEO4J_BIN_PATH", None), help="Path to Neo4j bin directory"
    ),
    java_home: str = typer.Option(
        os.getenv("JAVA_HOME", None), help="Path to Java installation"
    ),
    legacy_import: bool = typer.Option(
        os.getenv("LEGACY_IMPORT", "false").lower() == "true",
        help="Use legacy neo4j-admin import",
    ),
):
    """
    Run Neo4j bulk import using generated CSV headers and data.
    """
    try:
        typer.secho("\n=== Environment variable validation ===", fg=INFO, bold=True)
        warn_on_blank_env_vars(CRITICAL_ENV_VARS)
        neo4j_bin = Path(neo4j_bin_path) if neo4j_bin_path else None  # type: ignore
        java_home_path = Path(java_home) if java_home else None  # type: ignore
        typer.secho("Running Neo4j bulk import...", fg=typer.colors.WHITE)
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


def _execute_full_build(config: str, demo: bool = False) -> None:
    """Shared implementation for build pipelines (regular + demo)."""
    try:
        load_dotenv(config)
        typer.secho(f"Loaded config from: {config}", fg=typer.colors.WHITE)
        typer.secho("\n=== Environment variable validation ===", fg=INFO, bold=True)
        warn_on_blank_env_vars(CRITICAL_ENV_VARS)

        demo_already_enabled = os.getenv("DEMO_MODE", "false").lower() == "true"
        if demo:
            sample_override = apply_demo_overrides()
            demo_already_enabled = True
            typer.secho(
                f"Demo mode enabled: sampling {sample_override:.3f}% of the dataset",
                fg=INFO,
                bold=True,
            )
        elif demo_already_enabled:
            typer.secho("DEMO_MODE detected from environment.", fg=INFO)

        # Extract config values with defaults
        raw_core_dir = Path(os.getenv("TSV_CORE_DIR", "music_metadata"))
        raw_derived_dir = Path(os.getenv("TSV_DERIVED_DIR", "music_derived_metadata"))
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        csv_core_dir = Path(
            os.getenv("CSV_CORE_DIR", str(output_dir / "converted" / "core"))
        )
        csv_derived_dir = Path(
            os.getenv("CSV_DERIVED_DIR", str(output_dir / "converted" / "derived"))
        )
        sample_percent = float(os.getenv("SAMPLE_PERCENT", "100.0"))
        sample_seed = int(os.getenv("SAMPLE_SEED", "42"))
        delimiter = os.getenv("DELIMITER", "\t")
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
        vector_labels_env = os.getenv("VECTOR_LABELS")
        vector_labels = (
            split_labels_from_env(vector_labels_env)
            if vector_labels_env
            else DEFAULT_VECTOR_LABELS
        )

        sample_fraction = max(0.0, min(sample_percent, 100.0)) / 100.0

        checklist = print_preflight_summary(
            raw_core_dir=raw_core_dir,
            raw_derived_dir=raw_derived_dir,
            working_core_dir=csv_core_dir,
            working_derived_dir=csv_derived_dir,
            output_dir=output_dir,
            neo4j_bin_path=neo4j_bin_path,
            java_home=java_home,
            info_color=INFO,
        )
        ready_to_continue = typer.confirm(
            "Ready to continue? (raw dumps located, Neo4j stopped, Milvus + LM Studio embedding online, disk space OK)",
            default=False,
        )
        if not ready_to_continue or not all(checklist.values()):
            failed_items = [key for key, passed in checklist.items() if not passed]
            if failed_items:
                typer.secho(
                    "Build aborted. Fix the following checklist items before running again:",
                    fg=ERROR,
                )
                for item in failed_items:
                    typer.secho(f"  - {item}", fg=ERROR)
            else:
                typer.secho("Build aborted by user.", fg=ERROR)
            raise typer.Exit(1)

        headers_dir = output_dir / "core" / "headers"

        def _convert_dataset(label: str, source: Path, target: Path) -> None:
            typer.secho(
                f"Converting {label} dataset from {source} -> {target}",
                fg=INFO,
            )
            converted = handle_convert(source, target)
            typer.secho(
                f"✓ Converted {converted} {label.lower()} file(s) to CSV.", fg=SUCCESS
            )

        def _maybe_convert(label: str, source: Path, target: Path) -> None:
            if not source.exists():
                raise FileNotFoundError(
                    f"{label} source directory not found: {source}. Did you mount/extract the TSV/TAR dumps?"
                )
            if has_generated_files(target):
                typer.secho(
                    f"Existing CSVs detected for {label} in {target}.",
                    fg=INFO,
                )
                reuse = typer.confirm(
                    f"Reuse {label.lower()} CSV outputs instead of reconverting?",
                    default=True,
                )
                if reuse:
                    typer.secho(
                        f"Reusing {label.lower()} CSV directory: {target}", fg=INFO
                    )
                    return
                typer.secho(
                    f"Existing {label.lower()} CSVs will be overwritten.", fg=INFO
                )
            _convert_dataset(label, source, target)

        def _prompt_reuse_prepared_data() -> bool:
            if has_generated_files(headers_dir):
                typer.secho(
                    f"Existing header CSVs detected in {headers_dir}.",
                    fg=INFO,
                )
                reuse_existing = typer.confirm(
                    "Reuse current prepared data instead of regenerating headers/labels/relationships?",
                    default=True,
                )
                if reuse_existing:
                    typer.secho("Reusing previously generated CSV artifacts.", fg=INFO)
                else:
                    typer.secho(
                        "Headers and related CSV files will be overwritten.", fg=INFO
                    )
                return reuse_existing
            return False

        typer.secho("Starting full build process...", fg=INFO, bold=True)

        # Step 1: Convert TAR/TSV sources to CSV working sets
        typer.secho(
            "\nStep 1: Converting MusicBrainz dumps (TAR/TSV) into CSV working directories",
            fg=typer.colors.WHITE,
            bold=True,
        )
        _maybe_convert("Core", raw_core_dir, csv_core_dir)
        _maybe_convert("Derived", raw_derived_dir, csv_derived_dir)

        # Step 2: Prepare headers and data
        reuse_existing_data = _prompt_reuse_prepared_data()
        if reuse_existing_data:
            typer.secho(
                "\nStep 2 skipped: using previously prepared headers/labels/relationships.",
                fg=INFO,
                bold=True,
            )
        else:
            typer.secho(
                "\nStep 2: Preparing headers, labels, and relationships",
                fg=INFO,
                bold=True,
            )
            handle_prepare(
                core_dir=csv_core_dir,
                derived_dir=csv_derived_dir,
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
                typer.echo(
                    f"  - {output_dir.resolve()}/core/headers/ (core header files)"
                )
            if not skip_labels:
                typer.echo(
                    f"  - {output_dir.resolve()}/core/labeled/ (core labeled data)"
                )
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

        # Step 3: Import to Neo4j
        typer.secho(
            "\nStep 3: Importing CSVs into Neo4j (neo4j-admin bulk import)",
            fg=typer.colors.WHITE,
            bold=True,
        )
        handle_import_neo4j(
            headers_dir=headers_dir,
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

        typer.secho(
            "\nNeo4j import finished. Start the database (Neo4j Desktop) so the vector builder can stream nodes.",
            fg=INFO,
        )
        confirm_neo4j = typer.confirm(
            f"Is Neo4j running at bolt://{neo4j_host}:{neo4j_port}?",
            default=True,
        )
        if not confirm_neo4j:
            typer.secho("Vector build skipped because Neo4j is offline.", fg=ERROR)
            raise typer.Exit(1)

        typer.secho(
            f"Waiting for bolt://{neo4j_host}:{neo4j_port} to accept connections...",
            fg=INFO,
        )
        if not _wait_for_bolt(neo4j_host, neo4j_port):
            typer.secho(
                f"Neo4j at bolt://{neo4j_host}:{neo4j_port} did not respond within 2 minutes.",
                fg=ERROR,
            )
            raise typer.Exit(1)

        # Step 4: Build the vector database (Milvus + embeddings)
        typer.secho(
            "\nStep 4: Building Milvus vector database (requires LM Studio embedding model)",
            fg=typer.colors.WHITE,
            bold=True,
        )
        typer.secho(
            f"Embedding labels: {vector_labels}",
            fg=INFO,
        )
        populate(vector_labels)

        typer.secho(
            "\n🎉 Build finished! Neo4j + Milvus are ready for RAG queries.",
            fg=typer.colors.GREEN,
            bold=True,
        )
        typer.secho(
            "Switch LM Studio to your conversational LLM before running `query`.",
            fg=INFO,
        )

    except Exception as e:
        typer.secho(f"Error during build: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("build")
def build(
    config: str = typer.Option(".env", help="Path to config file (.env format)"),
    demo: bool = typer.Option(
        False,
        "--demo/--no-demo",
        help="Run the full pipeline with demo sampling (overrides SAMPLE_PERCENT/TEST_MODE).",
    ),
):
    """
    Run the complete pmllm build pipeline: convert TSV to CSV, prepare Neo4j data, import to Neo4j, and build vector database.

    This command performs a full end-to-end build of the RAG system:

    1. Converts MusicBrainz TSV dumps to CSV format
    2. Prepares Neo4j import files (headers, labels, relationships)
    3. Imports data into Neo4j using neo4j-admin bulk import
    4. Builds the Milvus vector database with embeddings

    Requires:
    - MusicBrainz TSV dumps in TSV_CORE_DIR and TSV_DERIVED_DIR
    - Neo4j Desktop stopped (for bulk import)
    - Milvus + MinIO running (docker-compose up -d)
    - LM Studio with embedding model active
    - Sufficient disk space (recommended 20GB+)

    Use --demo for quick testing with reduced sampling.
    """
    _execute_full_build(config=config, demo=demo)


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
        typer.secho(
            f"Building vector DB for labels: {label_list}", fg=typer.colors.WHITE
        )
        populate(label_list)
        typer.secho("✓ Vector DB build completed!", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("query")
def query(
    question: str = typer.Argument(..., help="The question to ask the RAG system"),
    k: int = typer.Option(5, help="Number of context documents to retrieve"),
):
    """
    Ask a question to the RAG system (Hybrid Search: Vector + Graph).
    """
    try:
        from db.vector.rag_pipeline import rag_answer

        typer.secho(f"Question: {question}", fg=typer.colors.WHITE)
        typer.secho("Thinking...", fg=typer.colors.WHITE)

        answer = rag_answer(question, k=k)

        typer.secho("\nAnswer:", fg=typer.colors.GREEN, bold=True)
        typer.echo(answer)

    except Exception as e:
        typer.secho(f"Error during query: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
