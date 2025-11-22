import os
from pathlib import Path
from typing import Optional
import typer
from db.neo4j.neo4j_importer import run_bulk_import, run_verification_queries


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