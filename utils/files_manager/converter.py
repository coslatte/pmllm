from pathlib import Path
import tarfile
import tempfile
from utils.files_manager.reader import ensure_tsv, convert_to_csv


class Converter:
    """
    Handles conversion of TSV files to CSV, including tar extraction.

    Note: MusicBrainz database dumps use TSV (Tab-Separated Values) format
    for their exported data files. This converter is designed to handle
    such dumps but works with any properly formatted TSV files.
    """

    @staticmethod
    def convert_tsvs_in_dir(src_dir: Path, out_dir: Path) -> int:
        """
        Convert all TSV files in src_dir to CSV format in out_dir.

        This function recursively processes all files in the source directory:
        - Extracts any .tar/.tar.gz files found
        - Converts all .tsv files to .csv format
        - Skips non-TSV files gracefully

        Note: MusicBrainz uses TSV format extensively in their database dumps
        and exports. This converter is optimized for such large-scale data
        processing but works with any valid TSV files.

        Args:
            src_dir: Source directory containing TSV files and/or tar archives
            out_dir: Output directory for generated CSV files

        Returns:
            Number of files successfully converted
        """
        all_files = [f for f in src_dir.rglob("*") if f.is_file()]

        print(f"Total files in {src_dir}: {len(all_files)}")

        converted = 0
        for file in all_files:
            try:
                # Check if it's a tar file
                if tarfile.is_tarfile(file):
                    print(f"Extracting tar: {file}")
                    temp_dir = Path(tempfile.mkdtemp())
                    with tarfile.open(file, "r") as tar:
                        tar.extractall(temp_dir)

                    # Now convert TSVs from temp_dir
                    for tsv_file in temp_dir.rglob("*"):
                        if tsv_file.is_file():
                            try:
                                ensure_tsv(tsv_file)
                                dst = out_dir / (
                                    tsv_file.name.replace(tsv_file.suffix, ".csv")
                                )
                                convert_to_csv(tsv_file, dst, src_delimiter="\t")

                                converted += 1
                                print(f"Converted from tar: {tsv_file} -> {dst}")
                            except ValueError:
                                pass  # Skip non-TSV in tar
                else:
                    # Treat as potential TSV
                    ensure_tsv(file)
                    dst = out_dir / (file.stem + ".csv")

                    convert_to_csv(file, dst, src_delimiter="\t")

                    converted += 1
                    print(f"Converted direct: {file} -> {dst}")
            except (ValueError, tarfile.TarError) as e:
                print(f"Skipped {file}: {e}")
        return converted