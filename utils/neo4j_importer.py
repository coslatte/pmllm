import subprocess
from pathlib import Path
from typing import Optional, Sequence


class Neo4jImportError(RuntimeError):
    """Raised when the Neo4j import process fails."""


def _run(
    cmd: Sequence[str],
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a shell command and return the CompletedProcess."""

    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise Neo4jImportError(
            f"Command failed: {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def run_bulk_import(
    headers_dir: Path,
    labeled_dir: Path,
    relationships_dir: Path,
    db_name: str = "musicbrainz.db",
    delimiter: str = "\t",
    array_delimiter: str = ";",
    skip_bad_relationships: bool = True,
    multiline_fields: bool = True,
    neo4j_bin_path: Optional[Path] = None,
) -> None:
    """Run neo4j-admin bulk import using generated header + data CSVs."""

    headers_dir = headers_dir.resolve()
    labeled_dir = labeled_dir.resolve()
    relationships_dir = relationships_dir.resolve()

    # Determine neo4j-admin command
    if neo4j_bin_path:
        neo4j_admin = str(neo4j_bin_path / "neo4j-admin.bat")
    else:
        neo4j_admin = "neo4j-admin"

    cmd = [
        neo4j_admin,
        "database",
        "import",
        "full",
        "--overwrite-destination=true",
        "--verbose",
        f"--nodes={headers_dir / 'artist_header.csv'},{labeled_dir / 'labeled_artist.csv'}",
        f"--nodes={headers_dir / 'recording_header.csv'},{labeled_dir / 'labeled_recording.csv'}",
        f"--nodes={headers_dir / 'release_header.csv'},{labeled_dir / 'labeled_release.csv'}",
        f"--nodes={headers_dir / 'work_header.csv'},{labeled_dir / 'labeled_work.csv'}",
        f"--nodes={headers_dir / 'area_header.csv'},{labeled_dir / 'labeled_area.csv'}",
        f"--relationships={headers_dir / 'artist_recording_rel_header.csv'},{relationships_dir / 'artist_recording_relationships.csv'}",
        f"--relationships={headers_dir / 'artist_release_rel_header.csv'},{relationships_dir / 'artist_release_relationships.csv'}",
        f"--delimiter={delimiter}",
        f"--array-delimiter={array_delimiter}",
        f"--skip-bad-relationships={'true' if skip_bad_relationships else 'false'}",
        f"--multiline-fields={'true' if multiline_fields else 'false'}",
        db_name,
    ]

    _run(cmd)


def run_verification_queries(
    user: str = "neo4j",
    password: str = "password",
    host: str = "localhost",
    port: int = 7687,
) -> None:
    """Run simple Cypher-shell verification queries."""

    base_cmd = [
        "cypher-shell",
        "-a",
        f"bolt://{host}:{port}",
        "-u",
        user,
        "-p",
        password,
    ]

    _run(base_cmd + ["CALL db.schema.visualization();"], check=False)
    _run(
        base_cmd
        + [
            "MATCH (n) RETURN labels(n)[0] as type, "
            "count(*) as count ORDER BY count DESC;",
        ],
        check=False,
    )
