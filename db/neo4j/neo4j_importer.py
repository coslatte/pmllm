import subprocess
import os
from pathlib import Path
from typing import Optional, Sequence


class Neo4jImportError(RuntimeError):
    """Raised when the Neo4j import process fails."""


def _run(
    cmd: Sequence[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """Run a shell command and return the CompletedProcess."""

    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        env=env,
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
    java_home: Optional[Path] = None,
    legacy_import: bool = False,
) -> None:
    """Run neo4j-admin bulk import using generated header + data CSVs."""

    print(f"neo4j_bin_path: {neo4j_bin_path}")
    print(f"headers_dir: {headers_dir}")
    print(f"labeled_dir: {labeled_dir}")
    print(f"relationships_dir: {relationships_dir}")

    headers_dir = headers_dir.resolve()
    labeled_dir = labeled_dir.resolve()
    relationships_dir = relationships_dir.resolve()

    # Determine neo4j-admin command
    import shutil

    has_local_admin = shutil.which("neo4j-admin") is not None
    has_docker = shutil.which("docker") is not None

    env = None
    if java_home:
        env = os.environ.copy()
        env["JAVA_HOME"] = str(java_home)
        # Prepend to PATH to ensure this java is found first
        env["PATH"] = str(java_home / "bin") + os.pathsep + env["PATH"]

    using_docker = False

    if neo4j_bin_path:
        executable = "neo4j-admin.bat" if os.name == "nt" else "neo4j-admin"
        neo4j_admin = neo4j_bin_path / executable
        cmd = [str(neo4j_admin)]
    elif has_local_admin:
        cmd = ["neo4j-admin"]
    elif has_docker:
        # Construct Docker command
        # We need to mount the input directories and the output data directory
        # Assuming the user wants to write to ./data/neo4j/data as per docker-compose.yml

        project_root = Path.cwd()
        data_mount = project_root / "data" / "neo4j" / "data"
        data_mount.mkdir(parents=True, exist_ok=True)

        print(
            f"Docker detected. Running import via container. Data will be written to: {data_mount}"
        )

        data_mount = data_mount.resolve()
        (data_mount / "databases").mkdir(parents=True, exist_ok=True)

        using_docker = True

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{headers_dir}:/headers",
            "-v",
            f"{labeled_dir}:/labeled",
            "-v",
            f"{relationships_dir}:/relationships",
            "-v",
            f"{data_mount}:/data",
            "neo4j:5.15.0",
            "neo4j-admin",
        ]
    else:
        raise Neo4jImportError("Neither 'neo4j-admin' nor 'docker' found in PATH.")

    def _resolve_local_data_dir() -> Path:
        env_dir = os.getenv("NEO4J_DATA_DIR")
        if env_dir:
            base = Path(env_dir).expanduser().resolve()
            if base.name != "databases":
                base = base / "databases"
            return base / db_name

        neo4j_home = os.getenv("NEO4J_HOME")
        if neo4j_home:
            home_path = Path(neo4j_home).expanduser().resolve()
            return home_path / "data" / "databases" / db_name

        if neo4j_bin_path:
            bin_root = neo4j_bin_path.resolve().parent.parent
            return bin_root / "data" / "databases" / db_name

        desktop_candidates = [
            Path.home() / ".Neo4jDesktop2" / "Data" / "dbmss",
            Path.home() / ".Neo4jDesktop" / "relate-data" / "dbmss",
            Path.home() / "AppData" / "Local" / "Neo4j" / "Relate" / "Data" / "dbmss",
        ]
        for container in desktop_candidates:
            if container.exists():
                dbms_dirs = sorted(container.glob("dbms-*"))
                for dbms_dir in dbms_dirs:
                    data_candidate = dbms_dir / "data" / "databases" / db_name
                    if data_candidate.parent.exists():
                        return data_candidate

        raise Neo4jImportError(
            "Set --neo4j-bin-path or NEO4J_DATA_DIR to use legacy neo4j-admin import."
        )

    if legacy_import:
        cmd.extend(["import"])
        if using_docker:
            into_path = f"/data/databases/{db_name}"
        else:
            data_dir = _resolve_local_data_dir()
            data_dir.parent.mkdir(parents=True, exist_ok=True)
            into_path = str(data_dir)
        cmd.append(f"--into={into_path}")
    else:
        cmd.extend(
            [
                "database",
                "import",
                "full",
                "--overwrite-destination=true",
                "--verbose",
            ]
        )

    # Helper to format paths for the command (local vs docker)
    def get_path(local_path: Path, mount_point: str) -> str:
        if has_local_admin or neo4j_bin_path:
            return str(local_path)
        return f"{mount_point}/{local_path.name}"

    # Add nodes - only if files exist
    node_files = [
        (headers_dir / "artist_header.csv", labeled_dir / "labeled_artist.csv"),
        (headers_dir / "recording_header.csv", labeled_dir / "labeled_recording.csv"),
        (headers_dir / "release_header.csv", labeled_dir / "labeled_release.csv"),
        (headers_dir / "work_header.csv", labeled_dir / "labeled_work.csv"),
        (headers_dir / "area_header.csv", labeled_dir / "labeled_area.csv"),
        (
            headers_dir / "release_group_header.csv",
            labeled_dir / "labeled_release_group.csv",
        ),
        (headers_dir / "tag_header.csv", labeled_dir / "labeled_tag.csv"),
    ]

    for header_file, data_file in node_files:
        if header_file.exists() and data_file.exists():
            cmd.append(
                f"--nodes={get_path(header_file, '/headers')},{get_path(data_file, '/labeled')}"
            )

    # Add relationships - only if files exist
    relationship_files = [
        (
            headers_dir / "artist_recording_rel_header.csv",
            relationships_dir / "artist_recording_relationships.csv",
        ),
        (
            headers_dir / "artist_release_rel_header.csv",
            relationships_dir / "artist_release_relationships.csv",
        ),
        (
            headers_dir / "recording_work_rel_header.csv",
            relationships_dir / "recording_work_relationships.csv",
        ),
        (
            headers_dir / "release_release_group_rel_header.csv",
            relationships_dir / "release_release_group_relationships.csv",
        ),
        (
            headers_dir / "artist_area_rel_header.csv",
            relationships_dir / "artist_area_relationships.csv",
        ),
        (
            headers_dir / "release_area_rel_header.csv",
            relationships_dir / "release_area_relationships.csv",
        ),
        (
            headers_dir / "recording_tag_rel_header.csv",
            relationships_dir / "recording_tag_relationships.csv",
        ),
        (
            headers_dir / "artist_tag_rel_header.csv",
            relationships_dir / "artist_tag_relationships.csv",
        ),
        (
            headers_dir / "release_tag_rel_header.csv",
            relationships_dir / "release_tag_relationships.csv",
        ),
    ]

    for header_file, data_file in relationship_files:
        if header_file.exists() and data_file.exists():
            cmd.append(
                f"--relationships={get_path(header_file, '/headers')},{get_path(data_file, '/relationships')}"
            )

    # neo4j-admin prefers 'TAB' for tab delimiter to avoid shell issues
    val_delimiter = "TAB" if delimiter == "\t" else delimiter
    cmd.append(f"--delimiter={val_delimiter}")
    cmd.append(f"--array-delimiter={array_delimiter}")
    if not legacy_import:
        cmd.append(
            f"--skip-bad-relationships={'true' if skip_bad_relationships else 'false'}"
        )
        cmd.append(f"--multiline-fields={'true' if multiline_fields else 'false'}")
        cmd.append(db_name)
    else:
        # Legacy import has different flags
        cmd.append("--bad-tolerance=1000")
        cmd.append(f"--multiline-fields={'true' if multiline_fields else 'false'}")
        # --into already added above

    print(f"Running command: {' '.join(cmd)}")
    result = _run(cmd, env=env)
    print("\n=== Neo4j Import Output ===")
    print(result.stdout)
    if result.stderr:
        print("=== Warnings/Errors ===")
        print(result.stderr)
    print("===========================\n")


def run_verification_queries(
    user: str = "neo4j",
    password: Optional[str] = None,
    host: str = "localhost",
    port: int = 7687,
) -> None:
    """Run simple Cypher-shell verification queries.

    Args:
        user: Neo4j username (default: "neo4j")
        password: Neo4j password (required, no default for security)
        host: Neo4j host (default: "localhost")
        port: Neo4j Bolt port (default: 7687)
    """

    if not password:
        raise ValueError(
            "Password is required for Neo4j verification queries. "
            "Set via --password argument or NEO4J_PASSWORD environment variable."
        )

    import shutil

    has_local_cypher = shutil.which("cypher-shell") is not None
    has_docker = shutil.which("docker") is not None

    if has_local_cypher:
        base_cmd = [
            "cypher-shell",
            "-a",
            f"bolt://{host}:{port}",
            "-u",
            user,
            "-p",
            password,
        ]
    elif has_docker:
        # Use docker to run cypher-shell
        # Note: host 'localhost' inside container refers to the container itself.
        # If connecting to host machine or another container, we need care.
        # If using docker-compose network, we can use service name if we were inside the network.
        # But here we are running a transient container.
        # 'host.docker.internal' works on Windows/Mac. On Linux it's trickier.
        # For simplicity, let's assume the user is running this script from the host
        # and the DB is exposed on localhost:7687.
        # We can use --network="host" on Linux, or host.docker.internal on Windows.

        # Since we are on Windows (pwsh), host.docker.internal should work.

        target_host = "host.docker.internal" if host == "localhost" else host

        base_cmd = [
            "docker",
            "run",
            "--rm",
            "neo4j:5.15.0",
            "cypher-shell",
            "-a",
            f"bolt://{target_host}:{port}",
            "-u",
            user,
            "-p",
            password,
        ]
    else:
        print(
            "Warning: cypher-shell not found and docker not available. Skipping verification."
        )
        return

    _run(base_cmd + ["CALL db.schema.visualization();"], check=False)
    _run(
        base_cmd
        + [
            "MATCH (n) RETURN labels(n)[0] as type, "
            "count(*) as count ORDER BY count DESC;",
        ],
        check=False,
    )
