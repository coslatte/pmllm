"""
Prepare MusicBrainz data for Neo4j import.

This module contains utilities specifically designed for processing MusicBrainz
database dumps, which use TSV (Tab-Separated Values) format extensively.
However, the core conversion functions can work with any properly formatted
TSV files following similar schemas.

MusicBrainz is a comprehensive music metadata database that exports its data
in TSV format for bulk processing and analysis.
"""

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Dict, Optional, Set, Any
from os import getenv

# Maximum CSV field size constant
# sys.maxsize may overflow on some platforms (e.g., Windows)
# Fallback to max 32-bit signed integer: 2^31 - 1
MAX_32BIT_INT = 2_147_483_647

# Increase CSV field size limit to handle large fields in MusicBrainz data
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(MAX_32BIT_INT)


NODE_HEADERS: Dict[str, str] = {
    "artist_header.csv": "id:ID(Artist),gid:string,name:string,sort_name:string,type:INT,area:INT,begin_date_year:INT,begin_date_month:INT,begin_date_day:INT,end_date_year:INT,end_date_month:INT,end_date_day:INT,ended:BOOLEAN,comment:string,:LABEL",
    "recording_header.csv": "id:ID(Recording),gid:string,name:string,artist_credit:INT,length:INT,comment:string,:LABEL",
    "release_header.csv": "id:ID(Release),gid:string,name:string,artist_credit:INT,release_group:INT,comment:string,:LABEL",
    "work_header.csv": "id:ID(Work),gid:string,name:string,type:INT,comment:string,:LABEL",
    "area_header.csv": "id:ID(Area),gid:string,name:string,type:INT,:LABEL",
    "release_group_header.csv": "id:ID(ReleaseGroup),gid:string,name:string,artist_credit:INT,type:INT,comment:string,:LABEL",
    "tag_header.csv": "id:ID(Tag),name:string,:LABEL",
    # Derived data headers
    "label_header.csv": "id:ID(Label),gid:string,name:string,sort_name:string,type:INT,area:INT,begin_date_year:INT,begin_date_month:INT,begin_date_day:INT,end_date_year:INT,end_date_month:INT,end_date_day:INT,ended:BOOLEAN,comment:string,:LABEL",
    "medium_header.csv": "id:ID(Medium),release:INT,position:INT,format:INT,name:string,:LABEL",
    "track_header.csv": "id:ID(Track),gid:string,name:string,artist_credit:INT,length:INT,position:INT,recording:INT,medium:INT,:LABEL",
    "place_header.csv": "id:ID(Place),gid:string,name:string,type:INT,area:INT,coordinates:string,comment:string,:LABEL",
    "event_header.csv": "id:ID(Event),gid:string,name:string,type:INT,begin_date_year:INT,begin_date_month:INT,begin_date_day:INT,end_date_year:INT,end_date_month:INT,end_date_day:INT,ended:BOOLEAN,comment:string,:LABEL",
    "genre_header.csv": "id:ID(Genre),gid:string,name:string,comment:string,:LABEL",
    "instrument_header.csv": "id:ID(Instrument),gid:string,name:string,type:INT,comment:string,:LABEL",
    "series_header.csv": "id:ID(Series),gid:string,name:string,type:INT,ordering_type:INT,comment:string,:LABEL",
    "url_header.csv": "id:ID(Url),url:string,:LABEL",
}

REL_HEADERS: Dict[str, str] = {
    "artist_recording_rel_header.csv": ":START_ID(Artist),:END_ID(Recording),position:INT,name:string,:TYPE",
    "artist_release_rel_header.csv": ":START_ID(Artist),:END_ID(Release),position:INT,name:string,:TYPE",
    "recording_work_rel_header.csv": ":START_ID(Recording),:END_ID(Work),:TYPE",
    "release_release_group_rel_header.csv": ":START_ID(Release),:END_ID(ReleaseGroup),:TYPE",
    "artist_area_rel_header.csv": ":START_ID(Artist),:END_ID(Area),:TYPE",
    "release_area_rel_header.csv": ":START_ID(Release),:END_ID(Area),:TYPE",
    "recording_tag_rel_header.csv": ":START_ID(Recording),:END_ID(Tag),:TYPE",
    "artist_tag_rel_header.csv": ":START_ID(Artist),:END_ID(Tag),:TYPE",
    "release_tag_rel_header.csv": ":START_ID(Release),:END_ID(Tag),:TYPE",
}

FILES_TO_LABEL: Dict[str, str] = {
    "artist": "Artist",
    "recording": "Recording",
    "release": "Release",
    "work": "Work",
    "area": "Area",
    "release_group": "ReleaseGroup",
    "tag": "Tag",
    # Derived data files
    "label": "Label",
    "medium": "Medium",
    "track": "Track",
    "place": "Place",
    "event": "Event",
    "genre": "Genre",
    "instrument": "Instrument",
    "series": "Series",
    "url": "Url",
}

# Mapping of input columns (0-based index) to output columns for each file type
# This ensures that the data matches the header definition even if the input file has extra columns
COLUMN_MAPPINGS: Dict[str, list[int]] = {
    "artist": [0, 1, 2, 3, 10, 11, 4, 5, 6, 7, 8, 9, 16, 13],
    "recording": [0, 1, 2, 3, 4, 5],
    "release": [0, 1, 2, 3, 4, 10],
    "work": [0, 1, 2, 3, 4],
    "area": [0, 1, 2, 3],
    "release_group": [0, 1, 2, 3, 4, 5],  # id, gid, name, artist_credit, type, comment
    "tag": [0, 1],  # id, name
    # Derived data mappings
    "label": [0, 1, 2, 3, 10, 11, 4, 5, 6, 7, 8, 9, 16, 13],  # Similar to artist
    "medium": [0, 1, 2, 3, 4],  # id, release, position, format, name
    "track": [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ],  # id, gid, name, artist_credit, length, position, recording, medium
    "place": [0, 1, 2, 3, 4, 5, 6],  # id, gid, name, type, area, coordinates, comment
    "event": [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
    ],  # Similar to artist but with event-specific fields
    "genre": [0, 1, 2, 3],  # id, gid, name, comment
    "instrument": [0, 1, 2, 3, 4],  # id, gid, name, type, comment
    "series": [0, 1, 2, 3, 4, 5],  # id, gid, name, type, ordering_type, comment
    "url": [0, 1],  # id, url
}


def resolve_table_path(
    table_name: str,
    core_dir: Path,
    derived_dir: Path,
    prefer_derived: bool = True,
) -> Optional[Path]:
    """Return the first matching path for a MusicBrainz table using preferred search order."""

    ordered_roots = []
    search_order = (
        (derived_dir, core_dir) if prefer_derived else (core_dir, derived_dir)
    )

    for root in search_order:
        if root is None:
            continue
        resolved = root.resolve()
        if resolved.exists() and resolved not in ordered_roots:
            ordered_roots.append(resolved)

    # Include common filename variants so we can read either raw TSV or converted CSV
    candidates = [table_name]
    if not table_name.endswith(".tsv"):
        candidates.append(f"{table_name}.tsv")
    if not table_name.endswith(".csv"):
        candidates.append(f"{table_name}.csv")

    for root in ordered_roots:
        for candidate in candidates:
            # First try exact match
            potential = root / candidate
            if potential.exists():
                return potential
            # Then try glob pattern for MusicBrainz prefixed files like mbdump-artist-*.tsv
            glob_pattern = f"*{candidate}"
            matches = list(root.glob(glob_pattern))
            if matches:
                # Return the first match (assuming there's only one)
                return matches[0]

    return None


def create_headers(
    headers_dir: Path, delimiter: str = "\t", encoding: str = "utf-8"
) -> None:
    """Create all required Neo4j header CSV files."""

    headers_dir = headers_dir.resolve()
    headers_dir.mkdir(parents=True, exist_ok=True)

    # Core headers (always created)
    core_headers = [
        "artist_header.csv",
        "recording_header.csv",
        "release_header.csv",
        "work_header.csv",
        "area_header.csv",
        "release_group_header.csv",
        "tag_header.csv",
    ]

    for filename in core_headers:
        header = NODE_HEADERS[filename]
        # Replace comma with the actual delimiter
        header_content = header.replace(",", delimiter)
        (headers_dir / filename).write_text(header_content + "\n", encoding=encoding)

    # Derived data headers (conditionally created)
    derived_headers = {
        "label_header.csv": getenv("PROCESS_LABELS", "true").lower() == "true",
        "medium_header.csv": getenv("PROCESS_MEDIUMS", "true").lower() == "true",
        "track_header.csv": getenv("PROCESS_TRACKS", "true").lower() == "true",
        "place_header.csv": getenv("PROCESS_PLACES", "true").lower() == "true",
        "event_header.csv": getenv("PROCESS_EVENTS", "true").lower() == "true",
        "genre_header.csv": getenv("PROCESS_GENRES", "true").lower() == "true",
        "instrument_header.csv": getenv("PROCESS_INSTRUMENTS", "true").lower()
        == "true",
        "series_header.csv": getenv("PROCESS_SERIES", "true").lower() == "true",
        "url_header.csv": getenv("PROCESS_URLS", "true").lower() == "true",
    }

    for filename, should_create in derived_headers.items():
        if should_create:
            header = NODE_HEADERS[filename]
            header_content = header.replace(",", delimiter)
            (headers_dir / filename).write_text(
                header_content + "\n", encoding=encoding
            )
            print(f"✅ Created derived header: {filename}")
        else:
            print(f"⏭️  Skipped derived header: {filename} (disabled)")

    # Relationship headers (always created for now)
    for filename, header in REL_HEADERS.items():
        header_content = header.replace(",", delimiter)
        (headers_dir / filename).write_text(header_content + "\n", encoding=encoding)

    print(f"✅ Header files created in {headers_dir}")


def prepare_artist_credit_relationships(
    mbdump_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    kept_artist_ids: Optional[Set[str]] = None,
    kept_recording_ids: Optional[Set[str]] = None,
    kept_release_ids: Optional[Set[str]] = None,
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
            raise FileNotFoundError(f"Required file not found: {path}")

    artist_credit_to_recording: Dict[str, str] = {}
    artist_credit_to_release: Dict[str, str] = {}

    with recording_path.open("r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
        for row in reader:
            if len(row) >= 4:
                row = ["" if field == "\\N" else field for field in row]
                if row[3] and row[0]:
                    artist_credit_to_recording[row[3]] = row[0]

    with release_path.open("r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
        for row in reader:
            if len(row) >= 4:
                row = ["" if field == "\\N" else field for field in row]
                if row[3] and row[0]:
                    artist_credit_to_release[row[3]] = row[0]

    recording_relationships_path = (
        relationships_dir / "artist_recording_relationships.csv"
    )
    release_relationships_path = relationships_dir / "artist_release_relationships.csv"

    with (
        artist_credit_name_path.open("r", encoding=encoding) as f,
        recording_relationships_path.open(
            "w", encoding=encoding, newline=""
        ) as out_rec,
        release_relationships_path.open("w", encoding=encoding, newline="") as out_rel,
    ):
        rec_writer = csv.writer(out_rec, delimiter=delimiter)
        rel_writer = csv.writer(out_rel, delimiter=delimiter)

        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
        for row in reader:
            if len(row) >= 4:
                # Clean \N values which represent NULL in MusicBrainz
                row = ["" if field == "\\N" else field for field in row]

                artist_credit = row[0]
                position = row[1]
                artist_id = row[2]
                name = row[3]

                recording_id = artist_credit_to_recording.get(artist_credit)
                if (
                    recording_id
                    and (kept_artist_ids is None or artist_id in kept_artist_ids)
                    and (
                        kept_recording_ids is None or recording_id in kept_recording_ids
                    )
                ):
                    rec_writer.writerow(
                        [artist_id, recording_id, position, name, "PERFORMED_ON"]
                    )

                release_id = artist_credit_to_release.get(artist_credit)
                if (
                    release_id
                    and (kept_artist_ids is None or artist_id in kept_artist_ids)
                    and (kept_release_ids is None or release_id in kept_release_ids)
                ):
                    rel_writer.writerow(
                        [artist_id, release_id, position, name, "RELEASED"]
                    )

    print(f"✅ Relationships generated in {relationships_dir}")


def prepare_recording_work_relationships(
    mbdump_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    kept_recording_ids: Optional[Set[str]] = None,
    kept_work_ids: Optional[Set[str]] = None,
) -> None:
    """Prepare Recording to Work relationships from l_recording_work table."""

    mbdump_dir = mbdump_dir.resolve()
    relationships_dir = relationships_dir.resolve()
    relationships_dir.mkdir(parents=True, exist_ok=True)

    recording_work_path = mbdump_dir / "l_recording_work"

    if not recording_work_path.exists():
        print(f"⚠️  Recording-Work relationships file not found: {recording_work_path}")
        return

    recording_work_relationships_path = (
        relationships_dir / "recording_work_relationships.csv"
    )

    with (
        recording_work_path.open("r", encoding=encoding) as f,
        recording_work_relationships_path.open(
            "w", encoding=encoding, newline=""
        ) as out,
    ):
        writer = csv.writer(out, delimiter=delimiter)
        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

        for row in reader:
            if len(row) >= 2:
                # Clean \N values
                row = ["" if field == "\\N" else field for field in row]
                recording_id, work_id = row[0], row[1]

                if (
                    kept_recording_ids is None or recording_id in kept_recording_ids
                ) and (kept_work_ids is None or work_id in kept_work_ids):
                    writer.writerow([recording_id, work_id, "BELONGS_TO"])

    print(f"✅ Recording-Work relationships generated in {relationships_dir}")


def prepare_release_release_group_relationships(
    mbdump_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    kept_release_ids: Optional[Set[str]] = None,
    kept_release_group_ids: Optional[Set[str]] = None,
) -> None:
    """Prepare Release to Release Group relationships from release table."""

    mbdump_dir = mbdump_dir.resolve()
    relationships_dir = relationships_dir.resolve()
    relationships_dir.mkdir(parents=True, exist_ok=True)

    release_path = mbdump_dir / "release"

    if not release_path.exists():
        print(f"⚠️  Release file not found: {release_path}")
        return

    release_release_group_relationships_path = (
        relationships_dir / "release_release_group_relationships.csv"
    )

    with (
        release_path.open("r", encoding=encoding) as f,
        release_release_group_relationships_path.open(
            "w", encoding=encoding, newline=""
        ) as out,
    ):
        writer = csv.writer(out, delimiter=delimiter)
        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

        for row in reader:
            if len(row) >= 5:
                # Clean \N values
                row = ["" if field == "\\N" else field for field in row]
                release_id, release_group_id = row[0], row[4]

                if (
                    release_group_id
                    and (kept_release_ids is None or release_id in kept_release_ids)
                    and (
                        kept_release_group_ids is None
                        or release_group_id in kept_release_group_ids
                    )
                ):
                    writer.writerow([release_id, release_group_id, "BELONGS_TO"])

    print(f"✅ Release-ReleaseGroup relationships generated in {relationships_dir}")


def prepare_area_relationships(
    mbdump_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    kept_artist_ids: Optional[Set[str]] = None,
    kept_release_ids: Optional[Set[str]] = None,
    kept_area_ids: Optional[Set[str]] = None,
) -> None:
    """Prepare Artist and Release to Area relationships."""

    mbdump_dir = mbdump_dir.resolve()
    relationships_dir = relationships_dir.resolve()
    relationships_dir.mkdir(parents=True, exist_ok=True)

    artist_path = mbdump_dir / "artist"
    release_path = mbdump_dir / "release"

    artist_area_relationships_path = relationships_dir / "artist_area_relationships.csv"
    release_area_relationships_path = (
        relationships_dir / "release_area_relationships.csv"
    )

    # Artist to Area relationships
    if artist_path.exists():
        with (
            artist_path.open("r", encoding=encoding) as f,
            artist_area_relationships_path.open(
                "w", encoding=encoding, newline=""
            ) as out,
        ):
            writer = csv.writer(out, delimiter=delimiter)
            reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

            for row in reader:
                if len(row) >= 12:
                    # Clean \N values
                    row = ["" if field == "\\N" else field for field in row]
                    artist_id, area_id = (
                        row[0],
                        row[10],
                    )  # area is at index 10 in artist table

                    if (
                        area_id
                        and (kept_artist_ids is None or artist_id in kept_artist_ids)
                        and (kept_area_ids is None or area_id in kept_area_ids)
                    ):
                        writer.writerow([artist_id, area_id, "FROM_AREA"])
    else:
        print(f"⚠️  Artist file not found: {artist_path}")

    # Release to Area relationships
    if release_path.exists():
        with (
            release_path.open("r", encoding=encoding) as f,
            release_area_relationships_path.open(
                "w", encoding=encoding, newline=""
            ) as out,
        ):
            writer = csv.writer(out, delimiter=delimiter)
            reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

            for row in reader:
                if len(row) >= 11:
                    # Clean \N values
                    row = ["" if field == "\\N" else field for field in row]
                    release_id, area_id = (
                        row[0],
                        row[10],
                    )  # area is at index 10 in release table

                    if (
                        area_id
                        and (kept_release_ids is None or release_id in kept_release_ids)
                        and (kept_area_ids is None or area_id in kept_area_ids)
                    ):
                        writer.writerow([release_id, area_id, "RELEASED_IN"])
    else:
        print(f"⚠️  Release file not found: {release_path}")

    print(f"✅ Area relationships generated in {relationships_dir}")


def prepare_tag_relationships(
    core_dir: Path,
    derived_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    kept_artist_ids: Optional[Set[str]] = None,
    kept_recording_ids: Optional[Set[str]] = None,
    kept_release_ids: Optional[Set[str]] = None,
    kept_tag_ids: Optional[Set[str]] = None,
) -> None:
    """Prepare Artist, Recording, and Release to Tag relationships."""

    core_dir = core_dir.resolve()
    derived_dir = derived_dir.resolve()
    relationships_dir = relationships_dir.resolve()
    relationships_dir.mkdir(parents=True, exist_ok=True)

    artist_tag_path = resolve_table_path(
        "artist_tag", core_dir, derived_dir, prefer_derived=False
    )
    recording_tag_path = resolve_table_path(
        "recording_tag", core_dir, derived_dir, prefer_derived=False
    )
    release_tag_path = resolve_table_path(
        "release_tag", core_dir, derived_dir, prefer_derived=False
    )

    artist_tag_relationships_path = relationships_dir / "artist_tag_relationships.csv"
    recording_tag_relationships_path = (
        relationships_dir / "recording_tag_relationships.csv"
    )
    release_tag_relationships_path = relationships_dir / "release_tag_relationships.csv"

    # Artist to Tag relationships
    if artist_tag_path:
        with (
            artist_tag_path.open("r", encoding=encoding) as f,
            artist_tag_relationships_path.open(
                "w", encoding=encoding, newline=""
            ) as out,
        ):
            writer = csv.writer(out, delimiter=delimiter)
            reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

            for row in reader:
                if len(row) >= 2:
                    # Clean \N values
                    row = ["" if field == "\\N" else field for field in row]
                    artist_id, tag_id = row[0], row[1]

                    if (kept_artist_ids is None or artist_id in kept_artist_ids) and (
                        kept_tag_ids is None or tag_id in kept_tag_ids
                    ):
                        writer.writerow([artist_id, tag_id, "HAS_TAG"])
    else:
        print(f"⚠️  Artist-Tag file not found in {core_dir} or {derived_dir}")

    # Recording to Tag relationships
    if recording_tag_path:
        with (
            recording_tag_path.open("r", encoding=encoding) as f,
            recording_tag_relationships_path.open(
                "w", encoding=encoding, newline=""
            ) as out,
        ):
            writer = csv.writer(out, delimiter=delimiter)
            reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

            for row in reader:
                if len(row) >= 2:
                    # Clean \N values
                    row = ["" if field == "\\N" else field for field in row]
                    recording_id, tag_id = row[0], row[1]

                    if (
                        kept_recording_ids is None or recording_id in kept_recording_ids
                    ) and (kept_tag_ids is None or tag_id in kept_tag_ids):
                        writer.writerow([recording_id, tag_id, "HAS_TAG"])
    else:
        print(f"⚠️  Recording-Tag file not found in {core_dir} or {derived_dir}")

    # Release to Tag relationships
    if release_tag_path:
        with (
            release_tag_path.open("r", encoding=encoding) as f,
            release_tag_relationships_path.open(
                "w", encoding=encoding, newline=""
            ) as out,
        ):
            writer = csv.writer(out, delimiter=delimiter)
            reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

            for row in reader:
                if len(row) >= 2:
                    # Clean \N values
                    row = ["" if field == "\\N" else field for field in row]
                    release_id, tag_id = row[0], row[1]

                    if (
                        kept_release_ids is None or release_id in kept_release_ids
                    ) and (kept_tag_ids is None or tag_id in kept_tag_ids):
                        writer.writerow([release_id, tag_id, "HAS_TAG"])
    else:
        print(f"⚠️  Release-Tag file not found in {core_dir} or {derived_dir}")

    print(f"✅ Tag relationships generated in {relationships_dir}")


def prepare_extended_relationships(
    core_dir: Path,
    derived_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    kept_node_ids: Optional[Dict[str, Set[str]]] = None,
) -> None:
    """Prepare additional relationship CSV files from extended l_* tables."""

    core_dir = core_dir.resolve()
    derived_dir = derived_dir.resolve()
    relationships_dir = relationships_dir.resolve()
    relationships_dir.mkdir(parents=True, exist_ok=True)

    # Read configuration for which relationships to skip or silence
    relationships_to_skip = (
        getenv("RELATIONSHIPS_TO_SKIP", "").split(",")
        if getenv("RELATIONSHIPS_TO_SKIP")
        else []
    )
    quiet_missing_extended = (
        getenv("QUIET_MISSING_EXTENDED_RELATIONSHIPS", "false").lower() == "true"
    )

    # Extended relationship files to process
    extended_relations = [
        (
            "l_label_release",
            "label_release_relationships.csv",
            ":START_ID(Label),:END_ID(Release),:TYPE",
        ),
        (
            "l_label_recording",
            "label_recording_relationships.csv",
            ":START_ID(Label),:END_ID(Recording),:TYPE",
        ),
        (
            "l_artist_place",
            "artist_place_relationships.csv",
            ":START_ID(Artist),:END_ID(Place),:TYPE",
        ),
        (
            "l_release_place",
            "release_place_relationships.csv",
            ":START_ID(Release),:END_ID(Place),:TYPE",
        ),
        (
            "l_recording_place",
            "recording_place_relationships.csv",
            ":START_ID(Recording),:END_ID(Place),:TYPE",
        ),
        (
            "l_artist_event",
            "artist_event_relationships.csv",
            ":START_ID(Artist),:END_ID(Event),:TYPE",
        ),
        (
            "l_release_event",
            "release_event_relationships.csv",
            ":START_ID(Release),:END_ID(Event),:TYPE",
        ),
        (
            "l_recording_event",
            "recording_event_relationships.csv",
            ":START_ID(Recording),:END_ID(Event),:TYPE",
        ),
        (
            "l_artist_genre",
            "artist_genre_relationships.csv",
            ":START_ID(Artist),:END_ID(Genre),:TYPE",
        ),
        (
            "l_release_genre",
            "release_genre_relationships.csv",
            ":START_ID(Release),:END_ID(Genre),:TYPE",
        ),
        (
            "l_recording_genre",
            "recording_genre_relationships.csv",
            ":START_ID(Recording),:END_ID(Genre),:TYPE",
        ),
        (
            "l_artist_instrument",
            "artist_instrument_relationships.csv",
            ":START_ID(Artist),:END_ID(Instrument),:TYPE",
        ),
        (
            "l_recording_url",
            "recording_url_relationships.csv",
            ":START_ID(Recording),:END_ID(Url),:TYPE",
        ),
        (
            "l_release_url",
            "release_url_relationships.csv",
            ":START_ID(Release),:END_ID(Url),:TYPE",
        ),
        (
            "l_artist_url",
            "artist_url_relationships.csv",
            ":START_ID(Artist),:END_ID(Url),:TYPE",
        ),
        (
            "l_work_url",
            "work_url_relationships.csv",
            ":START_ID(Work),:END_ID(Url),:TYPE",
        ),
        (
            "l_label_url",
            "label_url_relationships.csv",
            ":START_ID(Label),:END_ID(Url),:TYPE",
        ),
    ]

    for relation_file, output_file, header in extended_relations:
        if relation_file in relationships_to_skip:
            print(f"⏭️  Skipping relationship: {relation_file}")
            continue

        input_path = resolve_table_path(relation_file, core_dir, derived_dir)
        if not input_path:
            if not quiet_missing_extended:
                print(
                    f"⚠️  Extended relationship file '{relation_file}' not found in {derived_dir} or {core_dir}"
                )
            continue

        output_path = relationships_dir / output_file

        with input_path.open("r", encoding=encoding) as f:
            with output_path.open("w", encoding=encoding, newline="") as out:
                writer = csv.writer(out, delimiter=delimiter)
                reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)

                for row in reader:
                    if len(row) >= 3:
                        # Clean \N values
                        row = ["" if field == "\\N" else field for field in row]
                        start_id, end_id, link_type = row[0], row[1], row[2]

                        # Apply filtering if kept_node_ids provided
                        if kept_node_ids:
                            # Determine entity types from file name
                            # Map relation file names to entity types
                            entity_mappings = {
                                "l_label_release": ("Label", "Release"),
                                "l_label_recording": ("Label", "Recording"),
                                "l_artist_place": ("Artist", "Place"),
                                "l_release_place": ("Release", "Place"),
                                "l_recording_place": ("Recording", "Place"),
                                "l_artist_event": ("Artist", "Event"),
                                "l_release_event": ("Release", "Event"),
                                "l_recording_event": ("Recording", "Event"),
                                "l_artist_genre": ("Artist", "Genre"),
                                "l_release_genre": ("Release", "Genre"),
                                "l_recording_genre": ("Recording", "Genre"),
                                "l_artist_instrument": ("Artist", "Instrument"),
                                "l_recording_url": ("Recording", "Url"),
                                "l_release_url": ("Release", "Url"),
                                "l_artist_url": ("Artist", "Url"),
                                "l_work_url": ("Work", "Url"),
                                "l_label_url": ("Label", "Url"),
                            }

                            if relation_file in entity_mappings:
                                start_type, end_type = entity_mappings[relation_file]
                            else:
                                # Skip unknown relationship types
                                continue

                            if (
                                kept_node_ids.get(start_type)
                                and start_id not in kept_node_ids[start_type]
                            ) or (
                                kept_node_ids.get(end_type)
                                and end_id not in kept_node_ids[end_type]
                            ):
                                continue

                        writer.writerow([start_id, end_id, link_type])

        source = "derived" if input_path.is_relative_to(derived_dir) else "core"
        print(f"✅ Extended relationships generated: {output_file} (source: {source})")


def add_labels_to_data(
    core_dir: Path,
    derived_dir: Path,
    core_labeled_dir: Path,
    derived_labeled_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    sample_fraction: float = 1.0,
    rng: Optional[random.Random] = None,
) -> Optional[Dict[str, Set[str]]]:
    """Add label columns to existing MusicBrainz data files and return kept node IDs if sampling."""

    core_dir = core_dir.resolve()
    derived_dir = derived_dir.resolve()
    core_labeled_dir = core_labeled_dir.resolve()
    derived_labeled_dir = derived_labeled_dir.resolve()
    core_labeled_dir.mkdir(parents=True, exist_ok=True)
    derived_labeled_dir.mkdir(parents=True, exist_ok=True)

    # Read derived data processing options from environment
    process_derived = {
        "labels": getenv("PROCESS_LABELS", "true").lower() == "true",
        "mediums": getenv("PROCESS_MEDIUMS", "true").lower() == "true",
        "tracks": getenv("PROCESS_TRACKS", "true").lower() == "true",
        "places": getenv("PROCESS_PLACES", "true").lower() == "true",
        "events": getenv("PROCESS_EVENTS", "true").lower() == "true",
        "genres": getenv("PROCESS_GENRES", "true").lower() == "true",
        "instruments": getenv("PROCESS_INSTRUMENTS", "true").lower() == "true",
        "series": getenv("PROCESS_SERIES", "true").lower() == "true",
        "urls": getenv("PROCESS_URLS", "true").lower() == "true",
    }

    keep_all_rows = sample_fraction >= 0.9999 or rng is None
    kept_ids: Optional[Dict[str, Set[str]]] = {label: set() for label in FILES_TO_LABEL.values()} if not keep_all_rows else None

    # Core files (always processed)
    core_files = [
        "artist",
        "recording",
        "release",
        "work",
        "area",
        "release_group",
        "tag",
    ]

    for filename in core_files:
        label = FILES_TO_LABEL[filename]
        input_file = resolve_table_path(
            filename, core_dir, derived_dir, prefer_derived=False
        )
        if not input_file:
            print(
                f"⚠️  Core file '{filename}' not found in {core_dir} or fallback {derived_dir}"
            )
            continue

        output_file = core_labeled_dir / f"labeled_{filename}.csv"

        with input_file.open("r", encoding=encoding) as infile:
            with output_file.open("w", encoding=encoding, newline="") as outfile:
                reader = csv.reader(infile, delimiter=delimiter, quoting=csv.QUOTE_NONE)
                writer = csv.writer(outfile, delimiter=delimiter)

                mapping = COLUMN_MAPPINGS.get(filename)

                for row in reader:
                    # Clean \N values which represent NULL in MusicBrainz
                    row = ["" if field == "\\N" else field for field in row]

                    if (
                        not keep_all_rows
                        and rng is not None
                        and rng.random() > sample_fraction
                    ):
                        continue

                    if mapping:
                        # Select and reorder columns based on mapping
                        try:
                            new_row = [row[i] for i in mapping]
                            row = new_row
                        except IndexError:
                            # If row is shorter than expected, skip or pad?
                            # For now, let's just skip rows that are too short to match our schema
                            continue

                    row.append(label)
                    node_id = row[0] if row and row[0] else None
                    if node_id and kept_ids is not None:
                        kept_ids[label].add(node_id)
                    writer.writerow(row)

        source = "core" if input_file.is_relative_to(core_dir.resolve()) else "derived"
        print(f"✅ Label added to {input_file} -> {output_file} (source: {source})")

    # Derived data files (conditionally processed)
    derived_files = {
        "label": process_derived["labels"],
        "medium": process_derived["mediums"],
        "track": process_derived["tracks"],
        "place": process_derived["places"],
        "event": process_derived["events"],
        "genre": process_derived["genres"],
        "instrument": process_derived["instruments"],
        "series": process_derived["series"],
        "url": process_derived["urls"],
    }

    for filename, should_process in derived_files.items():
        if not should_process:
            print(f"⏭️  Skipping derived file: {filename} (disabled in config)")
            continue

        label = FILES_TO_LABEL[filename]
        input_file = resolve_table_path(filename, core_dir, derived_dir)
        if not input_file:
            print(
                f"⚠️  Derived file '{filename}' not found in {derived_dir} or fallback {core_dir}"
            )
            continue

        output_file = derived_labeled_dir / f"labeled_{filename}.csv"

        with input_file.open("r", encoding=encoding) as infile:
            with output_file.open("w", encoding=encoding, newline="") as outfile:
                reader = csv.reader(infile, delimiter=delimiter, quoting=csv.QUOTE_NONE)
                writer = csv.writer(outfile, delimiter=delimiter)

                mapping = COLUMN_MAPPINGS.get(filename)

                for row in reader:
                    # Clean \N values which represent NULL in MusicBrainz
                    row = ["" if field == "\\N" else field for field in row]

                    if (
                        not keep_all_rows
                        and rng is not None
                        and rng.random() > sample_fraction
                    ):
                        continue

                    if mapping:
                        # Select and reorder columns based on mapping
                        try:
                            new_row = [row[i] for i in mapping]
                            row = new_row
                        except IndexError:
                            # If row is shorter than expected, skip
                            continue

                    row.append(label)
                    node_id = row[0] if row and row[0] else None
                    if node_id and kept_ids is not None:
                        kept_ids[label].add(node_id)
                    writer.writerow(row)

        source = (
            "derived"
            if derived_dir and input_file.is_relative_to(derived_dir.resolve())
            else "core"
        )
        print(
            f"✅ Label added to derived {input_file} -> {output_file} (source: {source})"
        )

    return kept_ids


def run_pipeline(
    core_dir: Path,
    derived_dir: Path,
    output_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
    skip_headers: bool = False,
    skip_labels: bool = False,
    skip_relationships: bool = False,
    sample_fraction: float = 1.0,
    sample_seed: Optional[int] = None,
) -> None:
    """Run the full MusicBrainz-to-Neo4j CSV preparation pipeline.

    Args:
        core_dir: Directory containing core MusicBrainz TSV files
        derived_dir: Directory containing derived MusicBrainz TSV files
        output_dir: Base output directory for generated files
        delimiter: Field delimiter in input files
        encoding: Character encoding of input files
        skip_headers: Skip header file generation
        skip_labels: Skip labeled data generation
        skip_relationships: Skip relationship generation
        sample_fraction: Fraction of data to sample (0.0-1.0)
        sample_seed: Random seed for reproducible sampling
    """

    if sample_fraction <= 0 or sample_fraction > 1:
        raise ValueError("sample_fraction must be within (0, 1].")

    rng: Optional[random.Random] = None
    if sample_fraction < 0.9999:
        rng = random.Random(sample_seed)

    # Create output subdirectories
    core_output_dir = output_dir / "core"
    derived_output_dir = output_dir / "derived"

    core_output_dir.mkdir(parents=True, exist_ok=True)
    derived_output_dir.mkdir(parents=True, exist_ok=True)

    kept_node_ids: Optional[Dict[str, Set[str]]] = None

    if not skip_headers:
        # Core headers
        create_headers(
            headers_dir=core_output_dir / "headers",
            delimiter=delimiter,
            encoding=encoding,
        )

    if not skip_labels:
        kept_node_ids = add_labels_to_data(
            core_dir=core_dir,
            derived_dir=derived_dir,
            core_labeled_dir=core_output_dir / "labeled",
            derived_labeled_dir=derived_output_dir / "labeled",
            delimiter=delimiter,
            encoding=encoding,
            sample_fraction=sample_fraction,
            rng=rng,
        )
    elif sample_fraction < 0.9999:
        raise ValueError(
            "Sampling requires labeled data generation. Remove --skip-labels when sampling."
        )

    if not skip_relationships:
        if kept_node_ids is None and sample_fraction < 0.9999:
            raise ValueError(
                "Relationship sampling requires labeled data to identify kept node IDs."
            )

        # Generate core relationship types
        prepare_artist_credit_relationships(
            mbdump_dir=core_dir,
            relationships_dir=core_output_dir / "relationships",
            delimiter=delimiter,
            encoding=encoding,
            kept_artist_ids=kept_node_ids.get("Artist") if kept_node_ids else None,
            kept_recording_ids=kept_node_ids.get("Recording")
            if kept_node_ids
            else None,
            kept_release_ids=kept_node_ids.get("Release") if kept_node_ids else None,
        )

        prepare_recording_work_relationships(
            mbdump_dir=core_dir,
            relationships_dir=core_output_dir / "relationships",
            delimiter=delimiter,
            encoding=encoding,
            kept_recording_ids=kept_node_ids.get("Recording")
            if kept_node_ids
            else None,
            kept_work_ids=kept_node_ids.get("Work") if kept_node_ids else None,
        )

        prepare_release_release_group_relationships(
            mbdump_dir=core_dir,
            relationships_dir=core_output_dir / "relationships",
            delimiter=delimiter,
            encoding=encoding,
            kept_release_ids=kept_node_ids.get("Release") if kept_node_ids else None,
            kept_release_group_ids=kept_node_ids.get("ReleaseGroup")
            if kept_node_ids
            else None,
        )

        prepare_area_relationships(
            mbdump_dir=core_dir,
            relationships_dir=core_output_dir / "relationships",
            delimiter=delimiter,
            encoding=encoding,
            kept_artist_ids=kept_node_ids.get("Artist") if kept_node_ids else None,
            kept_release_ids=kept_node_ids.get("Release") if kept_node_ids else None,
            kept_area_ids=kept_node_ids.get("Area") if kept_node_ids else None,
        )

        prepare_tag_relationships(
            core_dir=core_dir,
            derived_dir=derived_dir,
            relationships_dir=core_output_dir / "relationships",
            delimiter=delimiter,
            encoding=encoding,
            kept_artist_ids=kept_node_ids.get("Artist") if kept_node_ids else None,
            kept_recording_ids=kept_node_ids.get("Recording")
            if kept_node_ids
            else None,
            kept_release_ids=kept_node_ids.get("Release") if kept_node_ids else None,
            kept_tag_ids=kept_node_ids.get("Tag") if kept_node_ids else None,
        )

        # Extended relationships (derived data)
        if getenv("PROCESS_EXTENDED_RELATIONSHIPS", "true").lower() == "true":
            prepare_extended_relationships(
                core_dir=core_dir,
                derived_dir=derived_dir,
                relationships_dir=derived_output_dir / "relationships",
                delimiter=delimiter,
                encoding=encoding,
                kept_node_ids=kept_node_ids,
            )


def validate_sampling_integrity(
    labeled_dir: Path,
    relationships_dir: Path,
    delimiter: str = "\t",
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """Validate graph integrity after sampling to detect orphaned nodes and broken relationships."""

    print("🔍 Validating sampling integrity...")

    # Load all node IDs
    node_ids = {}
    for file_path in labeled_dir.glob("labeled_*.csv"):
        entity_type = file_path.stem.replace("labeled_", "").title()
        ids = set()
        try:
            with file_path.open("r", encoding=encoding) as f:
                reader = csv.reader(f, delimiter=delimiter)
                next(reader, None)  # Skip header
                for row in reader:
                    if row and row[0]:
                        ids.add(row[0])
        except FileNotFoundError:
            continue
        node_ids[entity_type] = ids

    # Load all relationships and check for broken links
    relationship_stats = {}
    broken_relationships = {}

    for file_path in relationships_dir.glob("*.csv"):
        rel_name = (
            file_path.stem.replace("_relationships", "").replace("_", " ").title()
        )
        stats = {"total": 0, "broken": 0, "valid": 0}
        broken = []

        try:
            with file_path.open("r", encoding=encoding) as f:
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    if len(row) >= 2:
                        stats["total"] += 1
                        start_id, end_id = row[0], row[1]

                        # Determine entity types from relationship file name
                        # Handle both core and extended relationships
                        relationship_mappings = {
                            # Core relationships
                            "artist_recording": ("Artist", "Recording"),
                            "artist_release": ("Artist", "Release"),
                            "recording_work": ("Recording", "Work"),
                            "release_release_group": ("Release", "ReleaseGroup"),
                            "artist_area": ("Artist", "Area"),
                            "release_area": ("Release", "Area"),
                            "recording_tag": ("Recording", "Tag"),
                            "artist_tag": ("Artist", "Tag"),
                            "release_tag": ("Release", "Tag"),
                            # Extended relationships
                            "label_release": ("Label", "Release"),
                            "label_recording": ("Label", "Recording"),
                            "artist_place": ("Artist", "Place"),
                            "release_place": ("Release", "Place"),
                            "recording_place": ("Recording", "Place"),
                            "artist_event": ("Artist", "Event"),
                            "release_event": ("Release", "Event"),
                            "recording_event": ("Recording", "Event"),
                            "artist_genre": ("Artist", "Genre"),
                            "release_genre": ("Release", "Genre"),
                            "recording_genre": ("Recording", "Genre"),
                            "artist_instrument": ("Artist", "Instrument"),
                            "recording_url": ("Recording", "Url"),
                            "release_url": ("Release", "Url"),
                            "artist_url": ("Artist", "Url"),
                            "work_url": ("Work", "Url"),
                            "label_url": ("Label", "Url"),
                        }

                        # Find matching relationship type
                        start_type, end_type = None, None
                        for rel_key, (s_type, e_type) in relationship_mappings.items():
                            if rel_key in file_path.name:
                                start_type, end_type = s_type, e_type
                                break

                        if start_type is None or end_type is None:
                            continue

                        # Check if both nodes exist
                        start_exists = start_id in node_ids.get(start_type, set())
                        end_exists = end_id in node_ids.get(end_type, set())

                        if start_exists and end_exists:
                            stats["valid"] += 1
                        else:
                            stats["broken"] += 1
                            broken.append(
                                {
                                    "start_id": start_id,
                                    "end_id": end_id,
                                    "start_exists": start_exists,
                                    "end_exists": end_exists,
                                }
                            )

        except FileNotFoundError:
            continue

        relationship_stats[rel_name] = stats
        if broken:
            broken_relationships[rel_name] = broken[:10]  # Keep only first 10 examples

    # Calculate node connectivity
    connectivity = {}
    for entity_type, ids in node_ids.items():
        connectivity[entity_type] = {
            "total_nodes": len(ids),
            "estimated_connected": len(
                ids
            ),  # Simplified - all nodes are considered connected if they exist
        }

    # Summary
    total_relationships = sum(stats["total"] for stats in relationship_stats.values())
    broken_relationships_count = sum(
        stats["broken"] for stats in relationship_stats.values()
    )

    integrity_score = (
        (total_relationships - broken_relationships_count) / total_relationships
        if total_relationships > 0
        else 1.0
    )

    result = {
        "node_counts": {k: len(v) for k, v in node_ids.items()},
        "relationship_stats": relationship_stats,
        "broken_relationships": broken_relationships,
        "connectivity": connectivity,
        "summary": {
            "total_relationships": total_relationships,
            "broken_relationships": broken_relationships_count,
            "integrity_score": integrity_score,
            "status": "✅ GOOD"
            if integrity_score >= 0.95
            else "⚠️ WARNING"
            if integrity_score >= 0.80
            else "❌ CRITICAL",
        },
    }

    print(f"📊 Integrity Score: {integrity_score:.1%} ({result['summary']['status']})")
    print(f"🔗 Total Relationships: {total_relationships}")
    print(f"❌ Broken Relationships: {broken_relationships_count}")

    if broken_relationships_count > 0:
        print("⚠️  Found broken relationships in:")
        for rel_name, stats in relationship_stats.items():
            if stats["broken"] > 0:
                print(f"   - {rel_name}: {stats['broken']}/{stats['total']} broken")

    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="pmllm-csv-helper",
        description="Prepare MusicBrainz data for Neo4j",
    )
    parser.add_argument(
        "--core-dir",
        type=Path,
        default=Path("music_metadata"),
        help="Directory containing core MusicBrainz TSV files",
    )
    parser.add_argument(
        "--derived-dir",
        type=Path,
        default=Path("music_derived_metadata"),
        help="Directory containing derived MusicBrainz TSV files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Base output directory. Creates core/ and derived/ subdirectories automatically",
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
    parser.add_argument(
        "--mode",
        choices=["testing", "production"],
        help="Operation mode: 'testing' (50%% sample) or 'production' (100%% sample)",
    )
    parser.add_argument(
        "--sample-percent",
        type=float,
        default=None,
        help="Sample percentage for data reduction (0.0-1.0). Overrides --mode setting.",
    )
    parser.add_argument(
        "--sample-seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    parser.add_argument(
        "--validate-sampling",
        action="store_true",
        help="Run post-sampling validation to check graph integrity",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    # Determine sampling configuration based on mode
    if args.mode == "testing":
        sample_fraction = 0.5  # 50% for testing
        print("🧪 TESTING MODE: Using 50% sample for faster development cycles")
    elif args.mode == "production":
        sample_fraction = 1.0  # 100% for production
        print("🏭 PRODUCTION MODE: Using 100% data for complete dataset")
    else:
        sample_fraction = (
            args.sample_percent if args.sample_percent is not None else 1.0
        )
        if sample_fraction < 1.0:
            print(f"📊 CUSTOM SAMPLING: Using {sample_fraction:.0%} sample")
        else:
            print("📊 FULL DATASET: Using 100% data (no sampling)")

    # Override with explicit sample-percent if provided
    if args.sample_percent is not None:
        sample_fraction = args.sample_percent
        print(f"⚡ OVERRIDE: Using explicit sample percentage {sample_fraction:.0%}")

    print(f"🎲 Sample seed: {args.sample_seed}")
    print("Preparing MusicBrainz data for Neo4j...")

    run_pipeline(
        core_dir=args.core_dir,
        derived_dir=args.derived_dir,
        output_dir=args.output_dir,
        delimiter=args.delimiter,
        encoding=args.encoding,
        skip_headers=args.skip_headers,
        skip_labels=args.skip_labels,
        skip_relationships=args.skip_relationships,
        sample_fraction=sample_fraction,
        sample_seed=args.sample_seed,
    )

    print("Preparation completed!")
    print("\nGenerated files:")
    if not args.skip_headers:
        print(f"  - {args.output_dir.resolve()}/core/headers/ (core header files)")
    if not args.skip_labels:
        print(f"  - {args.output_dir.resolve()}/core/labeled/ (core labeled data)")
        print(
            f"  - {args.output_dir.resolve()}/derived/labeled/ (derived labeled data)"
        )
    if not args.skip_relationships:
        print(
            f"  - {args.output_dir.resolve()}/core/relationships/ (core relationship files)"
        )
        print(
            f"  - {args.output_dir.resolve()}/derived/relationships/ (derived relationship files)"
        )

    # Run validation if requested
    if args.validate_sampling and not args.skip_labels and not args.skip_relationships:
        print("\n" + "=" * 60)
        validation_result = validate_sampling_integrity(
            labeled_dir=args.labeled_dir,
            relationships_dir=args.relationships_dir,
            delimiter=args.delimiter,
            encoding=args.encoding,
        )

        # Summary
        summary = validation_result["summary"]
        print("\n📋 VALIDATION SUMMARY:")
        print(f"   Status: {summary['status']}")
        print(f"   Integrity Score: {summary['integrity_score']:.1%}")
        print(f"   Total Relationships: {summary['total_relationships']:,}")
        print(f"   Broken Relationships: {summary['broken_relationships']:,}")

        if summary["integrity_score"] < 0.95:
            print("\n⚠️  WARNING: Low integrity score detected!")
            print(
                "   Consider using a higher sample percentage or checking data sources."
            )
        else:
            print("\n✅ Graph integrity validated successfully!")


if __name__ == "__main__":
    main()
