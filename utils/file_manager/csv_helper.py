import argparse
import csv
import sys
from pathlib import Path
from typing import Dict

# Increase CSV field size limit to handle large fields in MusicBrainz data
csv.field_size_limit(sys.maxsize)


NODE_HEADERS: Dict[str, str] = {
    "artist_header.csv": "id:ID(Artist),gid:string,name:string,sort_name:string,type:INT,area:INT,begin_date_year:INT,begin_date_month:INT,begin_date_day:INT,end_date_year:INT,end_date_month:INT,end_date_day:INT,ended:BOOLEAN,comment:string,:LABEL",
    "recording_header.csv": "id:ID(Recording),gid:string,name:string,artist_credit:INT,length:INT,comment:string,:LABEL",
    "release_header.csv": "id:ID(Release),gid:string,name:string,artist_credit:INT,release_group:INT,comment:string,:LABEL",
    "work_header.csv": "id:ID(Work),gid:string,name:string,type:INT,comment:string,:LABEL",
    "area_header.csv": "id:ID(Area),gid:string,name:string,type:INT,:LABEL",
}

REL_HEADERS: Dict[str, str] = {
    "artist_recording_rel_header.csv": ":START_ID(Artist),:END_ID(Recording),position:INT,name:string,:TYPE",
    "artist_release_rel_header.csv": ":START_ID(Artist),:END_ID(Release),position:INT,name:string,:TYPE",
    "recording_work_rel_header.csv": ":START_ID(Recording),:END_ID(Work),:TYPE",
}

FILES_TO_LABEL: Dict[str, str] = {
    "artist": "Artist",
    "recording": "Recording",
    "release": "Release",
    "work": "Work",
    "area": "Area",
}


def create_headers(headers_dir: Path, encoding: str = "utf-8") -> None:
    """Create all required Neo4j header CSV files."""

    headers_dir = headers_dir.resolve()
    headers_dir.mkdir(parents=True, exist_ok=True)

    for filename, header in NODE_HEADERS.items():
        (headers_dir / filename).write_text(header + "\n", encoding=encoding)

    for filename, header in REL_HEADERS.items():
        (headers_dir / filename).write_text(header + "\n", encoding=encoding)

    print(f"✅ Archivos de cabecera creados en {headers_dir}")


def prepare_artist_credit_relationships(
    mbdump_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
) -> None:
    """Prepare relationship CSV files from artist_credit_name."""

    mbdump_dir = mbdump_dir.resolve()
    relationships_dir = relationships_dir.resolve()
    relationships_dir.mkdir(parents=True, exist_ok=True)

    recording_path = mbdump_dir / "recording"
    release_path = mbdump_dir / "release"
    artist_credit_name_path = mbdump_dir / "artist_credit_name"

    for path in (recording_path, release_path, artist_credit_name_path):
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo requerido: {path}")

    artist_credit_to_recording: Dict[str, str] = {}
    artist_credit_to_release: Dict[str, str] = {}

    with recording_path.open("r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if len(row) >= 4:
                artist_credit_to_recording[row[3]] = row[0]

    with release_path.open("r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if len(row) >= 4:
                artist_credit_to_release[row[3]] = row[0]

    recording_relationships_path = relationships_dir / "artist_recording_relationships.csv"
    release_relationships_path = relationships_dir / "artist_release_relationships.csv"

    with (
        artist_credit_name_path.open("r", encoding=encoding) as f,
        recording_relationships_path.open("w", encoding=encoding, newline="") as out_rec,
        release_relationships_path.open("w", encoding=encoding, newline="") as out_rel,
    ):
        rec_writer = csv.writer(out_rec)
        rel_writer = csv.writer(out_rel)

        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if len(row) >= 4:
                artist_credit = row[0]
                position = row[1]
                artist_id = row[2]
                name = row[3]

                recording_id = artist_credit_to_recording.get(artist_credit)
                if recording_id:
                    rec_writer.writerow(
                        [artist_id, recording_id, position, name, "PERFORMED_ON"]
                    )

                release_id = artist_credit_to_release.get(artist_credit)
                if release_id:
                    rel_writer.writerow(
                        [artist_id, release_id, position, name, "RELEASED"]
                    )

    print(f"✅ Relationships generated in {relationships_dir}")


def add_labels_to_data(
    mbdump_dir: Path,
    labeled_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
) -> None:
    """Add label columns to existing MusicBrainz data files."""

    mbdump_dir = mbdump_dir.resolve()
    labeled_dir = labeled_dir.resolve()
    labeled_dir.mkdir(parents=True, exist_ok=True)

    for filename, label in FILES_TO_LABEL.items():
        input_file = mbdump_dir / filename
        if not input_file.exists():
            raise FileNotFoundError(f"No se encontró el archivo requerido: {input_file}")

        output_file = labeled_dir / f"labeled_{input_file.name}.csv"

        with input_file.open("r", encoding=encoding) as infile:
            with output_file.open("w", encoding=encoding, newline="") as outfile:
                reader = csv.reader(infile, delimiter=delimiter)
                writer = csv.writer(outfile, delimiter=delimiter)

                for row in reader:
                    row.append(label)
                    writer.writerow(row)

        print(f"✅ Label added to {input_file} -> {output_file}")


def run_pipeline(
    mbdump_dir: Path,
    headers_dir: Path,
    labeled_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    skip_headers: bool = False,
    skip_labels: bool = False,
    skip_relationships: bool = False,
) -> None:
    """Run the full MusicBrainz-to-Neo4j CSV preparation pipeline."""

    if not skip_headers:
        create_headers(headers_dir=headers_dir, encoding=encoding)

    if not skip_labels:
        add_labels_to_data(
            mbdump_dir=mbdump_dir,
            labeled_dir=labeled_dir,
            delimiter=delimiter,
            encoding=encoding,
        )

    if not skip_relationships:
        prepare_artist_credit_relationships(
            mbdump_dir=mbdump_dir,
            relationships_dir=relationships_dir,
            delimiter=delimiter,
            encoding=encoding,
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="pmllm-csv-helper",
        description="Prepare MusicBrainz data for Neo4j",
    )
    parser.add_argument(
        "--mbdump",
        type=Path,
        default=Path("mbdump"),
        help="Directory containing the original MusicBrainz source files",
    )
    parser.add_argument(
        "--headers-dir",
        type=Path,
        default=Path("neo4j_headers"),
        help="Output directory for Neo4j header CSV files",
    )
    parser.add_argument(
        "--labeled-dir",
        type=Path,
        default=Path("labeled"),
        help="Output directory for labeled data CSV files",
    )
    parser.add_argument(
        "--relationships-dir",
        type=Path,
        default=Path("relationships"),
        help="Output directory for relationship CSV files",
    )
    parser.add_argument(
        "--delimiter",
        default="\t",
        help="Delimiter used in input files (default: tab)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding used for reading/writing (default: utf-8)",
    )
    parser.add_argument(
        "--skip-headers",
        action="store_true",
        help="Skip header CSV generation",
    )
    parser.add_argument(
        "--skip-labels",
        action="store_true",
        help="Skip labeled data generation",
    )
    parser.add_argument(
        "--skip-relationships",
        action="store_true",
        help="Skip relationship CSV generation",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    print("Preparing MusicBrainz data for Neo4j...")

    run_pipeline(
        mbdump_dir=args.mbdump,
        headers_dir=args.headers_dir,
        labeled_dir=args.labeled_dir,
        relationships_dir=args.relationships_dir,
        delimiter=args.delimiter,
        encoding=args.encoding,
        skip_headers=args.skip_headers,
        skip_labels=args.skip_labels,
        skip_relationships=args.skip_relationships,
    )

    print("Preparation completed!")
    print("\nGenerated files:")
    if not args.skip_headers:
        print(f"  - {args.headers_dir.resolve()} (header directory)")
    if not args.skip_labels:
        print(f"  - {args.labeled_dir.resolve()} (labeled data)")
    if not args.skip_relationships:
        print(
            f"  - {args.relationships_dir.resolve()} (relationship files)"
        )


if __name__ == "__main__":
    main()
