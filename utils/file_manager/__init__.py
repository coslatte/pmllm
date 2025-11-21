<<<<<<< HEAD
"""File management utilities for tabular data conversion and processing."""

from .converter import Converter
from .reader import (
    convert_to_csv,
    detect_delimiter,
    ensure_tsv,
    sample_rows,
    validate_tabular,
)
from .csv_helper import run_pipeline

__all__ = [
    "Converter",
    "convert_to_csv",
    "detect_delimiter",
    "ensure_tsv",
    "sample_rows",
    "validate_tabular",
    "run_pipeline",
]
=======
"""File management utilities for conversion and processing."""

from .converter import Converter
from .reader import convert_to_csv, ensure_tsv, sample_rows
from .csv_helper import run_pipeline

__all__ = ["Converter", "convert_to_csv", "ensure_tsv", "sample_rows", "run_pipeline"]
>>>>>>> 4c8ca2a7bcbb02c697fd2715883a66dd54803212
