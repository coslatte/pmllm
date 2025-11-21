from pathlib import Path
import csv
from typing import Dict, Iterable, Optional, Tuple
import tarfile
import tempfile
import sys


def _open_text(path: Path, encoding: str = "utf-8"):
    """Open path for text reading."""
    return open(str(path), "r", encoding=encoding)


def sample_rows(
    path: Path, n: int = 5, delimiter: str = "\t"
) -> Iterable[Tuple[int, list]]:
    """Yield first n parsed rows."""
    path = Path(path)
    with _open_text(path) as f:
        reader = csv.reader(f, delimiter=delimiter)
        for i, row in enumerate(reader):
            yield i, row
            if i + 1 >= n:
                break


def detect_delimiter(
    path: Path,
    candidates: Tuple[str, ...] = ("\t", ",", "|", ";"),
    sample_lines: int = 5,
) -> str:
    """Detect delimiter from a few lines."""
    path = Path(path)
    counts = {d: 0 for d in candidates}
    with _open_text(path) as f:
        for _ in range(sample_lines):
            line = f.readline()
            if not line:
                break
            for d in candidates:
                counts[d] += line.count(d)
    # return the delimiter with the largest count (default to tab)
    best = max(counts.items(), key=lambda kv: kv[1])[0]
    return best


def validate_tabular(
    path: Path,
    expected_cols: Optional[int] = None,
    delimiter: Optional[str] = None,
    header: bool = True,
    sample: int = 20,
) -> dict:
    """Validate delimiter and column counts."""
    path = Path(path)
    if delimiter is None:
        delimiter = detect_delimiter(path)

    col_counts: Dict[int, int] = {}
    rows_sampled = 0
    with _open_text(path) as f:
        reader = csv.reader(f, delimiter=delimiter)
        for i, row in enumerate(reader):
            rows_sampled += 1
            c = len(row)
            col_counts[c] = col_counts.get(c, 0) + 1
            if i + 1 >= sample:
                break

    ok = True
    if expected_cols is not None:
        ok = (expected_cols in col_counts) and (
            sum(v for k, v in col_counts.items() if k != expected_cols) == 0
        )
    else:
        # if more than one column count observed, warn (not OK)
        ok = len(col_counts) == 1

    return {
        "path": str(path),
        "delimiter": delimiter,
        "rows_sampled": rows_sampled,
        "col_counts": col_counts,
        "expected_cols": expected_cols,
        "ok": ok,
    }


def convert_to_csv(
    src: Path,
    dst: Path,
    src_delimiter: Optional[str] = None,
    dst_delimiter: str = ",",
    encoding: str = "utf-8",
) -> None:
    """Convert a delimited text file to CSV."""
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if src_delimiter is None:
        src_delimiter = detect_delimiter(src)

    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2_147_483_647)

    with (
        _open_text(src, encoding=encoding) as fr,
        open(str(dst), "w", encoding=encoding, newline="") as fw,
    ):
        reader = csv.reader(fr, delimiter=src_delimiter)
        writer = csv.writer(fw, delimiter=dst_delimiter)
        for row in reader:
            writer.writerow(row)


def check_integrity(path: Path, to_check: Path, sample: int = 50) -> None:
    """Print short integrity summary for two files."""
    path = Path(path)
    to_check = Path(to_check)

    s1 = validate_tabular(path, delimiter=None, sample=sample)
    s2 = validate_tabular(to_check, delimiter=None, sample=sample)

    print(f"Checked: {s1['path']}")
    print(
        f"  delimiter: {s1['delimiter']}, rows_sampled: {s1['rows_sampled']}, col_counts: {s1['col_counts']}"
    )
    print(f"Checked: {s2['path']}")
    print(
        f"  delimiter: {s2['delimiter']}, rows_sampled: {s2['rows_sampled']}, col_counts: {s2['col_counts']}"
    )

    if not s1["ok"]:
        print("WARNING: source file shows inconsistent column counts in sample")
    if not s2["ok"]:
        print("WARNING: target file shows inconsistent column counts in sample")

    # quick suggestion
    if s1["delimiter"] != s2["delimiter"]:
        print(
            "NOTE: delimiters differ between source and target; conversion may be required."
        )


def ensure_tsv(path: Path, sample: int = 10) -> None:
    """Raise if file is not tab-delimited."""

    info = validate_tabular(path, delimiter=None, sample=sample)
    if info["delimiter"] == "\t":
        return

    # Fallback: explicitly validate using tab delimiter in case text content contains
    # more commas/semicolons than tabs (common in free-form annotations).
    forced = validate_tabular(path, delimiter="\t", sample=sample)
    if len(forced["col_counts"]) == 1 and next(iter(forced["col_counts"])) > 1:
        return

    raise ValueError(f"Not TSV (tab-delimited): {path}")


def convert_path_to_csv(src: Path, out_dir: Path) -> int:
    """Convert a TSV file or all TSV files under a directory; returns count."""

    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def _convert_file(p: Path) -> None:
        ensure_tsv(p)
        dst = out_dir / (p.stem + ".csv")
        convert_to_csv(p, dst, src_delimiter="\t")

    converted = 0
    if src.is_file():
        _convert_file(src)
        converted += 1
    elif src.is_dir():
        for p in src.rglob("*.tsv"):
            if p.is_file():
                _convert_file(p)
                converted += 1
    else:
        raise FileNotFoundError(f"Path not found: {src}")

    return converted


def extract_tar_to_temp(tar_path: Path) -> Path:
    """Extract tar file to a temp dir and return the temp dir path."""

    temp_dir = Path(tempfile.mkdtemp())
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(temp_dir)
    return temp_dir


def process_tar_dir(tar_dir: Path, out_dir: Path) -> int:
    """Extract all tar files in dir, convert TSVs to CSV in out_dir; return converted count."""

    tar_dir = Path(tar_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    for tar_file in tar_dir.glob("*"):
        if tar_file.is_file():
            try:
                extract_dir = extract_tar_to_temp(tar_file)
                # Now convert TSVs from extract_dir to out_dir
                for tsv_file in extract_dir.rglob("*.tsv"):
                    if tsv_file.is_file():
                        ensure_tsv(tsv_file)
                        dst = out_dir / (tsv_file.stem + ".csv")
                        convert_to_csv(tsv_file, dst, src_delimiter="\t")
                        converted += 1
            except tarfile.TarError:
                # Skip if not a valid tar file
                continue
    return converted
