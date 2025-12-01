from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

from utils.files_manager.csv_helper import (
    EXTENDED_RELATIONSHIPS,
    FILES_TO_LABEL,
    NODE_HEADERS,
    REL_HEADERS,
)


def _ensure_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_bundle_file(
    header_line: str, data_path: Path, dest_path: Path, encoding: str
) -> None:
    _ensure_directory(dest_path)
    with dest_path.open("w", encoding=encoding, newline="") as dest:
        dest.write(header_line.rstrip("\n") + "\n")
        with data_path.open("r", encoding=encoding) as data:
            shutil.copyfileobj(data, dest)


def _build_relationship_header_map(delimiter: str) -> Dict[str, str]:
    rel_map: Dict[str, str] = {}
    for header_name, header_template in REL_HEADERS.items():
        key = header_name.replace("_rel_header.csv", "_relationships.csv")
        rel_map[key] = header_template.replace(",", delimiter)

    for _, output_file, header_template in EXTENDED_RELATIONSHIPS:
        rel_map[output_file] = header_template.replace(",", delimiter)

    return rel_map


def create_desktop_bundle(
    output_dir: Path,
    bundle_dir: Path | None = None,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    include_derived_nodes: bool = True,
    include_extended_relationships: bool = True,
) -> Dict[str, List[Path]]:
    output_dir = output_dir.resolve()
    if bundle_dir is None:
        bundle_dir = output_dir / "neo4j_desktop"
    bundle_dir = bundle_dir.resolve()

    headers_dir = output_dir / "core" / "headers"
    core_nodes_dir = output_dir / "core" / "labeled"
    derived_nodes_dir = output_dir / "derived" / "labeled"
    core_rels_dir = output_dir / "core" / "relationships"
    derived_rels_dir = output_dir / "derived" / "relationships"

    for required in (headers_dir, core_nodes_dir, core_rels_dir):
        if not required.exists():
            raise FileNotFoundError(
                f"Required directory not found: {required}. Run `prepare-neo4j` first."
            )

    nodes_target = bundle_dir / "nodes"
    rels_target = bundle_dir / "relationships"
    nodes_target.mkdir(parents=True, exist_ok=True)
    rels_target.mkdir(parents=True, exist_ok=True)

    created: Dict[str, List[Path]] = {"nodes": [], "relationships": []}

    node_sources: List[Path] = sorted(core_nodes_dir.glob("labeled_*.csv"))
    if include_derived_nodes and derived_nodes_dir.exists():
        node_sources.extend(sorted(derived_nodes_dir.glob("labeled_*.csv")))

    if not node_sources:
        raise FileNotFoundError(
            "No labeled node CSVs found. Run `prepare-neo4j` first."
        )

    for data_path in node_sources:
        stem = data_path.stem.replace("labeled_", "", 1)
        header_key = f"{stem}_header.csv"
        header_template = NODE_HEADERS.get(header_key)
        if header_template is None:
            continue
        header_line = header_template.replace(",", delimiter)
        label_name = FILES_TO_LABEL.get(stem, stem.title())
        dest_path = nodes_target / f"{label_name}.csv"
        _write_bundle_file(header_line, data_path, dest_path, encoding)
        created["nodes"].append(dest_path)

    rel_header_map = _build_relationship_header_map(delimiter)

    rel_sources: List[Path] = sorted(core_rels_dir.glob("*.csv"))
    if include_extended_relationships and derived_rels_dir.exists():
        rel_sources.extend(sorted(derived_rels_dir.glob("*.csv")))

    for rel_path in rel_sources:
        header_line = rel_header_map.get(rel_path.name)
        if header_line is None:
            continue
        dest_path = rels_target / rel_path.name
        _write_bundle_file(header_line, rel_path, dest_path, encoding)
        created["relationships"].append(dest_path)

    if not created["nodes"]:
        raise RuntimeError("No node bundle files were created.")

    if not created["relationships"]:
        raise RuntimeError("No relationship bundle files were created.")

    return created
