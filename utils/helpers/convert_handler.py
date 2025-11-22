from pathlib import Path
from utils.files_manager.converter import Converter


def handle_convert(src: Path, out_dir: Path) -> int:
    """
    Convert TSV files to CSV format.
    """
    if not src.is_dir():
        raise ValueError(f"Path must be a directory: {src}")

    out_dir.mkdir(parents=True, exist_ok=True)
    converted = Converter.convert_tsvs_in_dir(src, out_dir)
    return converted