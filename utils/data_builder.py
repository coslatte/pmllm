from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.helpers.convert_handler import handle_convert
from utils.helpers.prepare_handler import handle_prepare


@dataclass(frozen=True)
class DataBuildConfig:
    core_source: Path
    derived_source: Path
    output_dir: Path
    csv_core_dir: Optional[Path] = None
    csv_derived_dir: Optional[Path] = None
    delimiter: str = "\t"
    encoding: str = "utf-8"
    sample_fraction: float = 1.0
    sample_seed: int = 42
    skip_headers: bool = False
    skip_labels: bool = False
    skip_relationships: bool = False
    reuse_existing_converted: bool = True


@dataclass(frozen=True)
class DataBuildResult:
    core_converted: int
    derived_converted: int
    core_reused: bool
    derived_reused: bool
    core_csv_dir: Path
    derived_csv_dir: Path
    headers_dir: Path
    labeled_core_dir: Path
    labeled_derived_dir: Path
    relationships_core_dir: Path
    relationships_derived_dir: Path


def build_data(config: DataBuildConfig) -> DataBuildResult:
    """Run the end-to-end TAR/TSV -> CSV data preparation pipeline."""

    core_target = (config.csv_core_dir or config.output_dir / "converted" / "core").resolve()
    derived_target = (config.csv_derived_dir or config.output_dir / "converted" / "derived").resolve()
    core_target.mkdir(parents=True, exist_ok=True)
    derived_target.mkdir(parents=True, exist_ok=True)

    core_converted, core_reused = _convert_if_needed(
        label="core",
        source=config.core_source,
        target=core_target,
        reuse=config.reuse_existing_converted,
    )
    derived_converted, derived_reused = _convert_if_needed(
        label="derived",
        source=config.derived_source,
        target=derived_target,
        reuse=config.reuse_existing_converted,
    )

    handle_prepare(
        core_dir=core_target,
        derived_dir=derived_target,
        output_dir=config.output_dir,
        delimiter=config.delimiter,
        encoding=config.encoding,
        skip_headers=config.skip_headers,
        skip_labels=config.skip_labels,
        skip_relationships=config.skip_relationships,
        sample_fraction=config.sample_fraction,
        sample_seed=config.sample_seed,
    )

    headers_dir = config.output_dir / "core" / "headers"
    labeled_core_dir = config.output_dir / "core" / "labeled"
    labeled_derived_dir = config.output_dir / "derived" / "labeled"
    relationships_core_dir = config.output_dir / "core" / "relationships"
    relationships_derived_dir = config.output_dir / "derived" / "relationships"

    return DataBuildResult(
        core_converted=core_converted,
        derived_converted=derived_converted,
        core_reused=core_reused,
        derived_reused=derived_reused,
        core_csv_dir=core_target,
        derived_csv_dir=derived_target,
        headers_dir=headers_dir,
        labeled_core_dir=labeled_core_dir,
        labeled_derived_dir=labeled_derived_dir,
        relationships_core_dir=relationships_core_dir,
        relationships_derived_dir=relationships_derived_dir,
    )


def _convert_if_needed(label: str, source: Path, target: Path, reuse: bool) -> tuple[int, bool]:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(f"{label.title()} source directory not found: {source}")

    if reuse and _has_csv(target):
        return 0, True

    converted = handle_convert(source, target)
    return converted, False


def _has_csv(directory: Path) -> bool:
    if not directory.exists():
        return False
    return any(directory.rglob("*.csv"))
