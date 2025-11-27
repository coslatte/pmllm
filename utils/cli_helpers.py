"""Shared CLI helper utilities for pmllm commands."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import typer

RECOMMENDED_DISK_GB = 20.0


def split_labels_from_env(raw: str | None) -> list[str]:
    """Parse a comma-separated label list from an environment variable."""
    if not raw:
        return []
    return [label.strip() for label in raw.split(",") if label.strip()]


def has_generated_files(path: Path) -> bool:
    """Return True when the given directory exists and contains at least one file."""
    try:
        return path.exists() and any(path.iterdir())
    except PermissionError:
        return True


def apply_demo_overrides() -> float:
    """Force demo/test sampling settings and return the effective percent."""
    demo_sample = os.getenv("DEMO_SAMPLE_PERCENT", "0.1")
    demo_vector_sample = os.getenv("DEMO_VECTOR_SAMPLE_PERCENT", demo_sample)
    os.environ["DEMO_MODE"] = "true"
    os.environ["SAMPLE_PERCENT"] = demo_sample
    os.environ["TEST_MODE"] = "true"
    os.environ["TEST_SAMPLE_PERCENT"] = demo_sample
    os.environ["VECTOR_BUILD_SAMPLE_PERCENT"] = demo_vector_sample
    return float(demo_sample)


def path_status(label: str, path: Path | None, must_exist: bool = True) -> str:
    """Human-readable status for a filesystem path."""
    if path is None or not f"{path}".strip():
        return f"[MISSING] {label}: path not set"
    if must_exist and not path.exists():
        return f"[MISSING] {label}: {path}"
    return f"[OK] {label}: {path}"


def print_preflight_summary(
    *,
    raw_core_dir: Path,
    raw_derived_dir: Path | None,
    working_core_dir: Path,
    working_derived_dir: Path,
    output_dir: Path,
    neo4j_bin_path: Path | None,
    java_home: Path | None,
    info_color,
) -> dict[str, bool]:
    """Display and evaluate the pre-build checklist."""
    typer.secho("\n=== Pre-build checklist ===", fg=info_color, bold=True)
    status: dict[str, bool] = {
        "raw_core": raw_core_dir.exists(),
        "raw_derived": True,
        "output_parent": output_dir.parent.exists(),
        "neo4j_bin": neo4j_bin_path is not None and neo4j_bin_path.exists(),
        "java_home": java_home is not None and java_home.exists(),
        "embedding": bool(os.getenv("EMBEDDING_URL", "").strip()),
    }
    typer.echo(path_status("Raw TSV/TAR core directory", raw_core_dir))
    if raw_derived_dir and f"{raw_derived_dir}".strip():
        derived_exists = raw_derived_dir.exists()
        status["raw_derived"] = derived_exists
        typer.echo(path_status("Raw TSV/TAR derived directory", raw_derived_dir))
    else:
        typer.echo(
            "[INFO] TSV_DERIVED_DIR not set; derived tables will be skipped if disabled in .env."
        )
    typer.echo(
        path_status("Working CSV core directory", working_core_dir, must_exist=False)
    )
    typer.echo(
        path_status(
            "Working CSV derived directory", working_derived_dir, must_exist=False
        )
    )
    typer.echo(path_status("Output directory", output_dir.parent, must_exist=True))
    typer.echo(path_status("NEO4J_BIN_PATH", neo4j_bin_path or Path("")))
    typer.echo(path_status("JAVA_HOME", java_home or Path("")))

    embedding_url = os.getenv("EMBEDDING_URL", "").strip()
    if embedding_url:
        typer.echo(f"[OK] LM Studio embedding endpoint configured: {embedding_url}")
    else:
        typer.echo("[MISSING] EMBEDDING_URL (LM Studio embedding endpoint).")

    typer.echo("[REQUIRED] Neo4j Desktop must be STOPPED before running the import.")
    typer.echo(
        "[REQUIRED] LM Studio must expose the embedding model during the build. Switch back to the conversational LLM only after the build finishes."
    )
    typer.echo("[REQUIRED] docker-compose (Milvus/MinIO/etcd) must be RUNNING.")
    usage_base = output_dir if output_dir.exists() else output_dir.parent
    try:
        disk_usage = shutil.disk_usage(usage_base)
        free_gb = disk_usage.free / (1024**3)
        typer.echo(
            f"[INFO] Approx. free space: {free_gb:.1f} GB (recommended >= {RECOMMENDED_DISK_GB:.0f} GB)"
        )
        status["disk"] = free_gb >= RECOMMENDED_DISK_GB
    except FileNotFoundError:
        typer.echo(
            "[WARNING] Could not calculate free space because the path does not exist yet."
        )
        status["disk"] = False
    return status


def warn_on_blank_env_vars(env_vars: list[str]) -> dict[str, bool]:
    """Warn when any requested environment variable is unset or blank."""
    status: dict[str, bool] = {}
    for var in env_vars:
        raw = os.getenv(var)
        missing = raw is None or not raw.strip()
        status[var] = not missing
        if missing:
            typer.echo(f"[MISSING] {var}: environment variable not set.")
    return status
