import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
from utils.data_builder import DataBuildConfig, build_data
from utils.helpers.convert_handler import handle_convert
from utils.helpers.desktop_bundle_handler import create_desktop_bundle
from utils.helpers.import_handler import handle_import_neo4j
from utils.helpers.prepare_handler import handle_prepare

# Load environment variables from .env file immediately
load_dotenv(override=True)


app = typer.Typer()


class BuildProfile(str, Enum):
    FULL = "full"
    DEMO = "demo"
    IMPORT_ONLY = "neo4j-only"
    EMBEDDINGS_ONLY = "embeddings-only"
    CONVERSION_ONLY = "conversion-only"


@dataclass(frozen=True)
class BuildPlan:
    profile: BuildProfile
    label: str
    description: str
    run_conversion: bool
    run_preparation: bool
    run_import: bool
    run_vectors: bool
    force_demo: bool = False


BUILD_PLANS = {
    BuildProfile.FULL: BuildPlan(
        profile=BuildProfile.FULL,
        label="Full build",
        description="Convert + prepare + Neo4j import + embeddings",
        run_conversion=True,
        run_preparation=True,
        run_import=True,
        run_vectors=True,
    ),
    BuildProfile.DEMO: BuildPlan(
        profile=BuildProfile.DEMO,
        label="Demo build",
        description="Full build with demo sampling overrides",
        run_conversion=True,
        run_preparation=True,
        run_import=True,
        run_vectors=True,
        force_demo=True,
    ),
    BuildProfile.IMPORT_ONLY: BuildPlan(
        profile=BuildProfile.IMPORT_ONLY,
        label="Neo4j import only",
        description="Reuse existing CSV artifacts and run only the bulk import",
        run_conversion=False,
        run_preparation=False,
        run_import=True,
        run_vectors=False,
    ),
    BuildProfile.EMBEDDINGS_ONLY: BuildPlan(
        profile=BuildProfile.EMBEDDINGS_ONLY,
        label="Embeddings only",
        description="Skip to the Milvus/vector build step",
        run_conversion=False,
        run_preparation=False,
        run_import=False,
        run_vectors=True,
    ),
    BuildProfile.CONVERSION_ONLY: BuildPlan(
        profile=BuildProfile.CONVERSION_ONLY,
        label="Conversion only",
        description="Only convert TAR/TSV dumps into CSV working directories",
        run_conversion=True,
        run_preparation=False,
        run_import=False,
        run_vectors=False,
    ),
}

PLAN_SELECTION_ORDER = [
    BuildProfile.FULL,
    BuildProfile.DEMO,
    BuildProfile.IMPORT_ONLY,
    BuildProfile.EMBEDDINGS_ONLY,
    BuildProfile.CONVERSION_ONLY,
]


_DELIMITER_ESCAPES = {
    "\\t": "\t",
    "\\n": "\n",
    "\\r": "\r",
    "\\0": "\0",
    "\\\\": "\\",
}


def _normalize_delimiter(raw: Optional[str], fallback: str = "\t") -> str:
    """Return a one-character delimiter, expanding common escape sequences."""

    if not raw:
        return fallback
    resolved = _DELIMITER_ESCAPES.get(raw, raw)
    if len(resolved) != 1:
        raise typer.BadParameter(
            f"Delimiter must be a single character, received {resolved!r}",
            param_hint="delimiter",
        )
    return resolved


@dataclass(frozen=True)
class RuntimeCheck:
    name: str
    check_type: str  # "tcp" or "http"
    host: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    hint: Optional[str] = None


def _tcp_ping(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ping(url: str, timeout: float = 5.0) -> bool:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:  # type: ignore[call-arg]
            status = getattr(response, "status", None) or response.getcode()
            return status is not None and status < 500
    except (URLError, HTTPError, OSError):
        return False


def _collect_runtime_checks() -> tuple[List[RuntimeCheck], List[str]]:
    checks: List[RuntimeCheck] = []
    issues: List[str] = []

    neo4j_host = os.getenv("NEO4J_HOST", "localhost")
    neo4j_port = int(os.getenv("NEO4J_PORT", "7687"))
    checks.append(
        RuntimeCheck(
            name="Neo4j Bolt",
            check_type="tcp",
            host=neo4j_host,
            port=neo4j_port,
            hint="Start Neo4j Desktop or adjust NEO4J_HOST/NEO4J_PORT",
        )
    )

    milvus_host = os.getenv("MILVUS_HOST", "127.0.0.1")
    milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
    checks.append(
        RuntimeCheck(
            name="Milvus",
            check_type="tcp",
            host=milvus_host,
            port=milvus_port,
            hint="Ensure docker compose launched milvus-standalone",
        )
    )

    embedding_url = os.getenv("EMBEDDING_API_URL")
    if embedding_url:
        checks.append(
            RuntimeCheck(
                name="Embedding API",
                check_type="http",
                url=embedding_url,
                hint="Expected at pmllm-model-gateway /v1/embeddings",
            )
        )
    else:
        issues.append(
            "EMBEDDING_API_URL is not configured; point it at the model gateway embeddings endpoint"
        )

    llm_url = os.getenv("LLM_API_URL")
    if llm_url:
        checks.append(
            RuntimeCheck(
                name="LLM API",
                check_type="http",
                url=llm_url,
                hint="Expected at pmllm-model-gateway /v1/chat/completions",
            )
        )
    else:
        issues.append(
            "LLM_API_URL is not configured; set it to the model gateway chat endpoint"
        )

    return checks, issues


def _check_runtime_dependencies(retries: int = 5, delay: float = 2.0) -> List[str]:
    checks, issues = _collect_runtime_checks()
    failures = list(issues)

    for check in checks:
        success = False
        for attempt in range(retries):
            if check.check_type == "tcp" and check.host and check.port is not None:
                success = _tcp_ping(check.host, check.port)
            elif check.check_type == "http" and check.url:
                success = _http_ping(check.url)
            else:
                success = False

            if success:
                break

            time.sleep(delay)

        if not success:
            target = check.url or (
                f"{check.host}:{check.port}"
                if check.host and check.port
                else "unknown endpoint"
            )
            hint = f" ({check.hint})" if check.hint else ""
            failures.append(f"{check.name} is not reachable at {target}{hint}")

    return failures


def _start_compose_services(compose_file: Path) -> bool:
    compose_path = (
        compose_file if compose_file.is_absolute() else Path.cwd() / compose_file
    )

    if not compose_path.exists():
        typer.secho(
            f"docker-compose file not found at {compose_path}.", fg=ERROR, err=True
        )
        return False

    command = ["docker", "compose", "-f", str(compose_path), "up", "-d"]
    try:
        result = subprocess.run(
            command,
            cwd=str(compose_path.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except FileNotFoundError:
        typer.secho(
            "Docker is not installed or not available in PATH.", fg=ERROR, err=True
        )
        return False
    except subprocess.CalledProcessError as exc:
        typer.secho("docker compose up -d failed.", fg=ERROR, err=True)
        if exc.stderr:
            typer.echo(exc.stderr.strip(), err=True)
        return False

    stdout = result.stdout.strip()
    if stdout:
        typer.echo(stdout)
    typer.secho("✓ Docker services are running.", fg=SUCCESS)
    return True


def _prompt_for_build_plan() -> BuildPlan:
    typer.secho("\nBuild profile selection", fg=INFO, bold=True)
    typer.echo("Choose what the build command should execute:")
    ordered_plans = [BUILD_PLANS[profile] for profile in PLAN_SELECTION_ORDER]
    for idx, plan in enumerate(ordered_plans, start=1):
        typer.echo(f"  {idx}. {plan.label} — {plan.description}")

    choice = typer.prompt("Enter profile number", default="1")
    try:
        index = int(choice)
    except ValueError:
        typer.secho("Invalid selection. Please enter a number from the list.", fg=ERROR)
        raise typer.Exit(1)

    if not 1 <= index <= len(ordered_plans):
        typer.secho("Selection out of range.", fg=ERROR)
        raise typer.Exit(1)

    return ordered_plans[index - 1]


def _resolve_build_plan(
    profile_option: Optional[BuildProfile], demo_flag: bool
) -> BuildPlan:
    if profile_option and demo_flag:
        typer.secho(
            "Cannot combine --profile with --demo. Please choose one option.", fg=ERROR
        )
        raise typer.Exit(1)

    if profile_option:
        return BUILD_PLANS[profile_option]

    if demo_flag:
        return BUILD_PLANS[BuildProfile.DEMO]

    if not sys.stdin.isatty():
        typer.secho("No TTY detected. Defaulting to Full build profile.", fg=INFO)
        return BUILD_PLANS[BuildProfile.FULL]

    return _prompt_for_build_plan()


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


@app.command("start")
def start(
    compose_file: Path = typer.Option(
        Path(os.getenv("PMLLM_COMPOSE_FILE", "docker-compose.yml")),
        "--compose-file",
        "-c",
        help="Path to the docker-compose file that manages Milvus, MinIO, and the model gateway",
    ),
    skip_compose: bool = typer.Option(
        False,
        "--skip-compose",
        help="Do not run docker compose; assume services are already running",
    ),
    no_server: bool = typer.Option(
        False,
        "--no-server",
        help="Only (re)start services and perform health checks without launching FastAPI",
    ),
    host: str = typer.Option(
        os.getenv("API_HOST", "0.0.0.0"),
        "--host",
        help="Host interface for the FastAPI server",
    ),
    port: int = typer.Option(
        int(os.getenv("API_PORT", "8000")),
        "--port",
        help="Port for the FastAPI server",
    ),
    reload: bool = typer.Option(
        False,
        "--reload/--no-reload",
        help="Enable uvicorn auto-reload (development only)",
    ),
):
    """Start infrastructure services (docker compose) and launch the FastAPI server with health checks."""

    typer.secho("\n=== Starting pmllm platform ===", fg=INFO, bold=True)

    if skip_compose:
        typer.secho("Skipping docker compose startup (--skip-compose).", fg=INFO)
    else:
        typer.secho(
            "Bringing up docker services (Milvus, MinIO, model gateway)...",
            fg=typer.colors.WHITE,
        )
        if not _start_compose_services(compose_file):
            raise typer.Exit(1)

    typer.secho("Validating dependent services...", fg=typer.colors.WHITE)
    issues = _check_runtime_dependencies()
    if issues:
        typer.secho("\nMissing prerequisites detected:", fg=ERROR, bold=True)
        for issue in issues:
            typer.secho(f"  - {issue}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("All dependencies are reachable.", fg=SUCCESS)

    if no_server:
        typer.secho(
            "Infrastructure is ready. API server not started (--no-server).",
            fg=INFO,
        )
        return

    typer.secho(
        f"Starting FastAPI server at http://{host}:{port} (reload={'on' if reload else 'off'})...",
        fg=typer.colors.WHITE,
    )
    try:
        import uvicorn
    except ImportError:
        typer.secho(
            "Uvicorn is not installed. Add it to your environment to run the API server.",
            fg=ERROR,
            err=True,
        )
        raise typer.Exit(1)

    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
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
        typer.secho(
            f"✓ Converted {converted} file(s) to: {out_dir.resolve()}",
            fg=typer.colors.GREEN,
        )
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("build-data")
def build_data_command(
    core_dir: str = typer.Option(
        os.getenv("TSV_CORE_DIR", "music_metadata"),
        help="Directory with core MusicBrainz dumps (TSV/TAR)",
    ),
    derived_dir: str = typer.Option(
        os.getenv("TSV_DERIVED_DIR", "music_derived_metadata"),
        help="Directory with derived MusicBrainz dumps (TSV/TAR)",
    ),
    output_dir: str = typer.Option(
        os.getenv("OUTPUT_DIR", "output"),
        help="Base output directory containing prepared CSV artifacts",
    ),
    csv_core_dir: str = typer.Option(
        os.getenv("CSV_CORE_DIR", None),
        help="Optional working directory for converted core CSV files",
    ),
    csv_derived_dir: str = typer.Option(
        os.getenv("CSV_DERIVED_DIR", None),
        help="Optional working directory for converted derived CSV files",
    ),
    sample_percent: float = typer.Option(
        float(os.getenv("SAMPLE_PERCENT", "100.0")),
        help="Percent of rows to keep when preparing CSVs",
    ),
    sample_seed: int = typer.Option(
        int(os.getenv("SAMPLE_SEED", "42")),
        help="Random seed controlling the sampling step",
    ),
    delimiter: str = typer.Option(
        os.getenv("DELIMITER", "\t"),
        help="Delimiter used by the TSV files (\\t for tab)",
    ),
    encoding: str = typer.Option(
        os.getenv("ENCODING", "utf-8"),
        help="File encoding for read/write operations",
    ),
    skip_headers: bool = typer.Option(
        os.getenv("SKIP_HEADERS", "false").lower() == "true",
        help="Skip header generation",
    ),
    skip_labels: bool = typer.Option(
        os.getenv("SKIP_LABELS", "false").lower() == "true",
        help="Skip labeled node CSV generation",
    ),
    skip_relationships: bool = typer.Option(
        os.getenv("SKIP_RELATIONSHIPS", "false").lower() == "true",
        help="Skip relationship CSV generation",
    ),
    reuse_converted: bool = typer.Option(
        True,
        help="Reuse existing converted CSV directories when they already exist",
    ),
):
    """Convert TAR/TSV dumps and prepare Neo4j-ready CSV artifacts in one call."""

    try:
        sample_fraction = max(0.0, min(sample_percent, 100.0)) / 100.0
        delim = _normalize_delimiter(delimiter)
        config = DataBuildConfig(
            core_source=Path(core_dir),
            derived_source=Path(derived_dir),
            output_dir=Path(output_dir),
            csv_core_dir=Path(csv_core_dir) if csv_core_dir else None,
            csv_derived_dir=Path(csv_derived_dir) if csv_derived_dir else None,
            delimiter=delim,
            encoding=encoding,
            sample_fraction=sample_fraction,
            sample_seed=sample_seed,
            skip_headers=skip_headers,
            skip_labels=skip_labels,
            skip_relationships=skip_relationships,
            reuse_existing_converted=reuse_converted,
        )

        result = build_data(config)

        typer.secho("✓ Data build completed.", fg=typer.colors.GREEN)
        typer.echo(
            f"Core CSVs: {result.core_csv_dir} ({'reused' if result.core_reused else 'converted'})"
        )
        typer.echo(
            f"Derived CSVs: {result.derived_csv_dir} ({'reused' if result.derived_reused else 'converted'})"
        )
        typer.echo(f"Headers: {result.headers_dir}")
        if not skip_labels:
            typer.echo(f"Core labeled data: {result.labeled_core_dir}")
            typer.echo(f"Derived labeled data: {result.labeled_derived_dir}")
        if not skip_relationships:
            typer.echo(f"Core relationships: {result.relationships_core_dir}")
            typer.echo(f"Derived relationships: {result.relationships_derived_dir}")
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
        delim = _normalize_delimiter(delimiter)
        handle_prepare(
            core_dir=Path(core_dir),
            derived_dir=Path(derived_dir),
            output_dir=Path(output_dir),
            delimiter=delim,
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
            delimiter=_normalize_delimiter(delimiter),
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
            delimiter=_normalize_delimiter(delimiter),
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


def _has_data_rows(csv_path: Path) -> bool:
    """Return True when the CSV file contains at least one non-empty line."""

    try:
        with csv_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    return True
    except (OSError, UnicodeDecodeError):
        return False
    return False


def _assert_sampled_nodes_exist(
    labeled_dir: Path,
    required_slugs: Sequence[str],
    sample_percent: float,
) -> None:
    """Ensure essential labeled CSVs exist and contain data before import."""

    missing: List[str] = []
    empty: List[str] = []

    for slug in required_slugs:
        csv_file = labeled_dir / f"labeled_{slug}.csv"
        if not csv_file.exists():
            missing.append(slug)
            continue
        if not _has_data_rows(csv_file):
            empty.append(slug)

    if missing or empty:
        issues: List[str] = []
        if missing:
            issues.append(f"missing files ({', '.join(missing)})")
        if empty:
            issues.append(f"empty files ({', '.join(empty)})")
        detail = "; ".join(issues)
        raise RuntimeError(
            "Neo4j import aborted: prepared dataset contains no sampled rows for "
            f"{detail}. Current SAMPLE_PERCENT={sample_percent:.4f}%. Increase the "
            "sampling percentage and regenerate the CSV artifacts."
        )


def _execute_full_build(config: str, plan: BuildPlan) -> None:
    """Shared implementation for build pipelines (regular + demo)."""
    try:
        load_dotenv(config)
        typer.secho(f"Loaded config from: {config}", fg=typer.colors.WHITE)
        typer.secho("\n=== Environment variable validation ===", fg=INFO, bold=True)
        warn_on_blank_env_vars(CRITICAL_ENV_VARS)

        typer.secho(f"\nSelected build profile: {plan.label}", fg=INFO, bold=True)
        typer.echo(plan.description)
        typer.echo(f"  • Convert dumps: {'yes' if plan.run_conversion else 'skip'}")
        typer.echo(
            f"  • Prepare CSV artifacts: {'yes' if plan.run_preparation else 'skip'}"
        )
        typer.echo(f"  • Neo4j import: {'yes' if plan.run_import else 'skip'}")
        typer.echo(f"  • Vector build: {'yes' if plan.run_vectors else 'skip'}")

        demo_already_enabled = os.getenv("DEMO_MODE", "false").lower() == "true"
        if plan.force_demo:
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
        delimiter = _normalize_delimiter(os.getenv("DELIMITER", "\t"))
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

        checklist = {}
        if plan.run_conversion or plan.run_preparation or plan.run_import:
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

        readiness_requirements = []
        if plan.run_conversion or plan.run_preparation:
            readiness_requirements.append("raw dumps located")
        if plan.run_import:
            readiness_requirements.append("Neo4j Desktop stopped")
        if plan.run_vectors:
            readiness_requirements.append("Milvus + model gateway online")
        readiness_prompt = "Ready to continue?"
        if readiness_requirements:
            readiness_prompt += " (" + ", ".join(readiness_requirements) + ")"

        ready_to_continue = typer.confirm(readiness_prompt, default=False)

        if ready_to_continue and checklist and not all(checklist.values()):
            failed_items = [key for key, passed in checklist.items() if not passed]
            typer.secho(
                "Warning: Some requirements are not satisfied:",
                fg=typer.colors.RED,
                bold=True,
            )
            typer.echo(", ".join(failed_items))
            sure = typer.confirm("Continue anyway?", default=False)
            if not sure:
                typer.secho("Build aborted by user.", fg=ERROR)
                raise typer.Exit(1)
        elif not ready_to_continue:
            typer.secho("Build aborted by user.", fg=ERROR)
            raise typer.Exit(1)

        headers_dir = output_dir / "core" / "headers"
        labeled_core_dir = output_dir / "core" / "labeled"
        relationships_core_dir = output_dir / "core" / "relationships"

        def _require_path(path: Path, description: str) -> None:
            if not path.exists():
                typer.secho(f"Required {description} not found at {path}.", fg=ERROR)
                raise typer.Exit(1)

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

        typer.secho("Starting build process...", fg=INFO, bold=True)

        # Step 1: Convert TAR/TSV sources to CSV working sets
        if plan.run_conversion:
            typer.secho(
                "\nStep 1: Converting MusicBrainz dumps (TAR/TSV) into CSV working directories",
                fg=typer.colors.WHITE,
                bold=True,
            )
            _maybe_convert("Core", raw_core_dir, csv_core_dir)
            _maybe_convert("Derived", raw_derived_dir, csv_derived_dir)
        else:
            typer.secho(
                "\nStep 1 skipped: reusing existing converted CSV directories.",
                fg=INFO,
                bold=True,
            )
            if plan.run_preparation:
                _require_path(csv_core_dir, "core converted CSV directory")
                _require_path(csv_derived_dir, "derived converted CSV directory")

        # Step 2: Prepare headers and data
        if plan.run_preparation:
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
        else:
            typer.secho(
                "\nStep 2 skipped: reusing prepared Neo4j CSV artifacts.",
                fg=INFO,
                bold=True,
            )
            if plan.run_import:
                _require_path(headers_dir, "headers directory")
                _require_path(labeled_core_dir, "core labeled directory")
                _require_path(relationships_core_dir, "core relationships directory")

        # Step 3: Import to Neo4j
        if plan.run_import:
            typer.secho(
                "\nStep 3: Importing CSVs into Neo4j (neo4j-admin bulk import)",
                fg=typer.colors.WHITE,
                bold=True,
            )
            _require_path(headers_dir, "headers directory")
            _require_path(labeled_core_dir, "core labeled directory")
            _require_path(relationships_core_dir, "core relationships directory")
            _assert_sampled_nodes_exist(
                labeled_dir=labeled_core_dir,
                required_slugs=(
                    "artist",
                    "recording",
                    "release",
                    "release_group",
                ),
                sample_percent=sample_percent,
            )
            handle_import_neo4j(
                headers_dir=headers_dir,
                labeled_dir=labeled_core_dir,
                relationships_dir=relationships_core_dir,
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
        else:
            typer.secho(
                "\nStep 3 skipped: Neo4j import not requested for this profile.",
                fg=INFO,
                bold=True,
            )

        if plan.run_vectors:
            if plan.run_import:
                typer.secho(
                    "\nNeo4j import finished. Start the database (Neo4j Desktop) so the vector builder can stream nodes.",
                    fg=INFO,
                )
            else:
                typer.secho(
                    "\nVector build requested. Ensure Neo4j is already running with the desired dataset.",
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
                "\nStep 4: Building Milvus vector database (requires the embedding API to be online)",
                fg=typer.colors.WHITE,
                bold=True,
            )
            typer.secho(
                f"Embedding labels: {vector_labels}",
                fg=INFO,
            )
            populate(vector_labels)

        typer.secho(
            f"\n🎉 Build profile '{plan.label}' completed successfully.",
            fg=typer.colors.GREEN,
            bold=True,
        )
        if plan.run_vectors:
            typer.secho(
                "Switch the model gateway back to the conversational LLM before running `query`.",
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
    profile: Optional[BuildProfile] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Select which build profile to execute (full, demo, neo4j-only, embeddings-only, conversion-only).",
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
    - MusicBrainz TSV dumps in TSV_CORE_DIR and TSV_DERIVED_DIR (needed for conversion/preparation)
    - Neo4j Desktop stopped (when running the bulk import step)
    - Milvus + model gateway online (when running the embeddings/vector step)
    - Sufficient disk space (recommended 20GB+)

    Use --demo or --profile demo for quick testing with reduced sampling.
    """
    plan = _resolve_build_plan(profile_option=profile, demo_flag=demo)
    _execute_full_build(config=config, plan=plan)


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
