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
    """Crear todos los archivos de cabecera necesarios."""

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
    """Preparar archivos de relaciones desde artist_credit_name."""

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

    print(f"✅ Relaciones generadas en {relationships_dir}")


def add_labels_to_data(
    mbdump_dir: Path,
    labeled_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
) -> None:
    """Añadir etiquetas a los archivos de datos existentes."""

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

        print(f"✅ Etiqueta añadida a {input_file} -> {output_file}")


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
    """Ejecutar la preparación completa de datos."""

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
        description="Preparar datos de MusicBrainz para Neo4j",
    )
    parser.add_argument(
        "--mbdump",
        type=Path,
        default=Path("mbdump"),
        help="Directorio que contiene los archivos fuente de MusicBrainz",
    )
    parser.add_argument(
        "--headers-dir",
        type=Path,
        default=Path("neo4j_headers"),
        help="Directorio de salida para las cabeceras CSV",
    )
    parser.add_argument(
        "--labeled-dir",
        type=Path,
        default=Path("labeled"),
        help="Directorio de salida para los archivos con etiquetas",
    )
    parser.add_argument(
        "--relationships-dir",
        type=Path,
        default=Path("relationships"),
        help="Directorio de salida para los archivos de relaciones",
    )
    parser.add_argument(
        "--delimiter",
        default="\t",
        help="Delimitador de los archivos de entrada (por defecto tabulación)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Codificación de lectura/escritura (por defecto utf-8)",
    )
    parser.add_argument(
        "--skip-headers",
        action="store_true",
        help="Omitir la generación de archivos de cabecera",
    )
    parser.add_argument(
        "--skip-labels",
        action="store_true",
        help="Omitir la creación de archivos con etiquetas",
    )
    parser.add_argument(
        "--skip-relationships",
        action="store_true",
        help="Omitir la generación de archivos de relaciones",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    print("🎵 Preparando datos de MusicBrainz para Neo4j...")

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

    print("🎉 Preparación completada!")
    print("\n📁 Archivos generados:")
    if not args.skip_headers:
        print(f"  - {args.headers_dir.resolve()} (directorio con cabeceras)")
    if not args.skip_labels:
        print(f"  - {args.labeled_dir.resolve()} (datos con etiquetas)")
    if not args.skip_relationships:
        print(
            f"  - {args.relationships_dir.resolve()} (archivos de relaciones)"
        )


if __name__ == "__main__":
    main()
