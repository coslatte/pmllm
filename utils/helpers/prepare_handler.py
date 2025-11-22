from pathlib import Path
from utils.files_manager.csv_helper import run_pipeline


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