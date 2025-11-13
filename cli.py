from pathlib import Path
import argparse
from utils.reader import convert_path_to_csv


class CLI:
    """TSV to CSV converter CLI."""

    @staticmethod
    def run(argv=None) -> None:
        """Parse args, verify TSV, convert to CSV, and print a summary."""
        parser = argparse.ArgumentParser(
            prog="pmllm-cli",
            description="Convert TSV file(s) to CSV into an output folder",
        )
        parser.add_argument(
            "path",
            help="Path to a TSV file or a directory containing .tsv files",
        )
        parser.add_argument(
            "-o",
            "--out",
            default="converted",
            help="Output directory for generated CSV files (default: converted)",
        )
        args = parser.parse_args(argv)

        src = Path(args.path)
        out_dir = Path(args.out)

        count = convert_path_to_csv(src, out_dir)
        print(f"Converted {count} file(s) to: {out_dir.resolve()}")
