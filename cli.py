from pathlib import Path
import argparse
import sys
from utils.file_manager.converter import Converter
from utils.file_manager.csv_helper import run_pipeline
from db.neo4j.neo4j_importer import run_bulk_import, run_verification_queries


class CLI:
    """Command-line interface for tabular data conversion and Neo4j import tools."""

    @staticmethod
    def _handle_convert(args: argparse.Namespace) -> None:
        """
        Convert TSV files to CSV format.

        This command processes all TSV files found in the specified directory,
        including those inside tar archives. It's designed to handle large
        datasets like MusicBrainz dumps but works with any properly formatted
        TSV files.

        Note: MusicBrainz database exports use TSV format extensively.
        """
        src = Path(args.path)
        if not src.is_dir():
            raise ValueError(f"Path must be a directory: {src}")

        out_dir = Path(args.out) if args.out else Path.cwd() / "out_csv"
        out_dir.mkdir(parents=True, exist_ok=True)

        converted = Converter.convert_tsvs_in_dir(src, out_dir)
        print(f"Converted {converted} file(s) to: {out_dir.resolve()}")

    @staticmethod
    def _handle_prepare(args: argparse.Namespace) -> None:
        print("Preparing MusicBrainz data for Neo4j...")
        sample_percent = max(0.0, min(args.sample_percent, 100.0))
        sample_fraction = sample_percent / 100.0
        run_pipeline(
            mbdump_dir=Path(args.mbdump),
            headers_dir=Path(args.headers_dir),
            labeled_dir=Path(args.labeled_dir),
            relationships_dir=Path(args.relationships_dir),
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
            print(f"  - {Path(args.headers_dir).resolve()} (directory with headers)")
        if not args.skip_labels:
            print(f"  - {Path(args.labeled_dir).resolve()} (labeled data)")
        if not args.skip_relationships:
            print(f"  - {Path(args.relationships_dir).resolve()} (relationship files)")

    @staticmethod
    def _handle_import_neo4j(args: argparse.Namespace) -> None:
        headers_dir = Path(args.headers_dir)
        labeled_dir = Path(args.labeled_dir)
        relationships_dir = Path(args.relationships_dir)
        neo4j_bin_path = Path(args.neo4j_bin_path) if args.neo4j_bin_path else None
        java_home = Path(args.java_home) if args.java_home else None

        print("Running Neo4j bulk import...")
        run_bulk_import(
            headers_dir=headers_dir,
            labeled_dir=labeled_dir,
            relationships_dir=relationships_dir,
            db_name=args.db_name,
            delimiter=args.delimiter,
            array_delimiter=args.array_delimiter,
            skip_bad_relationships=not args.allow_bad_relationships,
            multiline_fields=args.multiline_fields,
            neo4j_bin_path=neo4j_bin_path,
            java_home=java_home,
            legacy_import=args.legacy_import,
        )
        print("Neo4j bulk import completed.")

        if args.verify:
            import os
            password = args.password or os.getenv("NEO4J_PASSWORD")
            if not password:
                print("Warning: No password provided. Set NEO4J_PASSWORD environment variable or use --password")
                return
            
            print("Running verification Cypher queries...")
            run_verification_queries(
                user=args.user,
                password=password,
                host=args.host,
                port=args.port,
            )
            print("Verification queries completed.")

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="pmllm-cli",
            description="""
            Command-line tools for tabular data processing and Neo4j import.
            
            This tool provides utilities for:
            - Converting TSV files to CSV (including tar extraction)
            - Preparing MusicBrainz data for Neo4j import
            - Running Neo4j bulk imports
            
            Note: MusicBrainz database dumps use TSV format extensively.
            The conversion tools work with any properly formatted TSV files.
            """,
        )
        subparsers = parser.add_subparsers(dest="command")

        convert_parser = subparsers.add_parser(
            "convert",
            help="Convert TSV files to CSV format (extracts tars, processes all TSVs found)",
        )
        convert_parser.add_argument(
            "path",
            help="Path to a directory containing .tsv files",
        )
        convert_parser.add_argument(
            "-o",
            "--out",
            help="Output directory for generated CSV files (default: out_csv in current dir)",
        )
        convert_parser.set_defaults(handler=CLI._handle_convert)

        prepare_parser = subparsers.add_parser(
            "prepare-neo4j",
            help="Generate headers, labels, and relationships for Neo4j",
        )
        prepare_parser.add_argument(
            "--mbdump",
            default="mbdump",
            help="Directory with the original MusicBrainz files",
        )
        prepare_parser.add_argument(
            "--headers-dir",
            default="neo4j_headers",
            help="Output directory for headers",
        )
        prepare_parser.add_argument(
            "--labeled-dir",
            default="labeled",
            help="Output directory for labeled files",
        )
        prepare_parser.add_argument(
            "--relationships-dir",
            default="relationships",
            help="Output directory for relationship files",
        )
        prepare_parser.add_argument(
            "--sample-percent",
            type=float,
            default=100.0,
            help="Percent of rows to keep when generating CSVs (default: 100%%)",
        )
        prepare_parser.add_argument(
            "--sample-seed",
            type=int,
            default=42,
            help="Random seed controlling which rows are kept during sampling",
        )
        prepare_parser.add_argument(
            "--delimiter",
            default="\t",
            help="Delimiter used by input files",
        )
        prepare_parser.add_argument(
            "--encoding",
            default="utf-8",
            help="Encoding used when reading and writing files",
        )
        prepare_parser.add_argument(
            "--skip-headers",
            action="store_true",
            help="Skip header generation",
        )
        prepare_parser.add_argument(
            "--skip-labels",
            action="store_true",
            help="Skip creation of labeled files",
        )
        prepare_parser.add_argument(
            "--skip-relationships",
            action="store_true",
            help="Skip relationship generation",
        )
        prepare_parser.set_defaults(handler=CLI._handle_prepare)

        import_parser = subparsers.add_parser(
            "import-neo4j",
            help="Run Neo4j bulk import using generated CSV headers and data",
        )
        import_parser.add_argument(
            "--headers-dir",
            default="neo4j_headers",
            help="Directory containing Neo4j header CSV files",
        )
        import_parser.add_argument(
            "--labeled-dir",
            default="labeled",
            help="Directory containing labeled data CSV files",
        )
        import_parser.add_argument(
            "--relationships-dir",
            default="relationships",
            help="Directory containing relationship CSV files",
        )
        import_parser.add_argument(
            "--db-name",
            default="musicbrainz.db",
            help="Target Neo4j database name for bulk import",
        )
        import_parser.add_argument(
            "--delimiter",
            default="\t",
            help="Field delimiter used in CSV files",
        )
        import_parser.add_argument(
            "--array-delimiter",
            default=";",
            help="Array delimiter used in CSV fields",
        )
        import_parser.add_argument(
            "--allow-bad-relationships",
            action="store_true",
            help="Do not skip bad relationships (by default they are skipped)",
        )
        import_parser.add_argument(
            "--multiline-fields",
            action="store_true",
            default=True,
            help="Treat fields as multiline (default: true)",
        )
        import_parser.add_argument(
            "--verify",
            action="store_true",
            help="Run simple verification Cypher queries after import",
        )
        import_parser.add_argument(
            "--user",
            default="neo4j",
            help="Neo4j username for verification queries",
        )
        import_parser.add_argument(
            "--password",
            default=None,
            help="Neo4j password for verification queries (use environment variable NEO4J_PASSWORD or pass via CLI)",
        )
        import_parser.add_argument(
            "--host",
            default="localhost",
            help="Neo4j host for verification queries",
        )
        import_parser.add_argument(
            "--port",
            type=int,
            default=7687,
            help="Neo4j Bolt port for verification queries",
        )
        import_parser.add_argument(
            "--neo4j-bin-path",
            default=None,
            help="Path to Neo4j bin directory (e.g., for Neo4j Desktop installations)",
        )
        import_parser.add_argument(
            "--java-home",
            default=None,
            help="Path to Java installation (JAVA_HOME) to use for the import process",
        )
        import_parser.add_argument(
            "--legacy-import",
            action="store_true",
            help="Use legacy neo4j-admin import instead of modern database import (for older Neo4j versions)",
        )
        import_parser.set_defaults(handler=CLI._handle_import_neo4j)

        return parser

    @staticmethod
    def run(argv=None) -> None:
        """Parse args, execute requested command, and print a summary."""

        parser = CLI._build_parser()
        raw_args = sys.argv[1:] if argv is None else list(argv)

        # Backwards compatibility: if command omitted, assume "convert".
        # But only if there are args and the first one isn't a known command.
        # If no args, print help.
        if not raw_args:
            parser.print_help()
            return

        if raw_args[0] not in {"convert", "prepare-neo4j", "import-neo4j", "-h", "--help"}:
             # If the user provided paths but no command, assume 'convert' for legacy reasons
             # But be careful not to swallow errors if they just typed a typo command
             raw_args.insert(0, "convert")

        args = parser.parse_args(raw_args)

        if not hasattr(args, "handler"):
            parser.print_help()
            return

        args.handler(args)


if __name__ == "__main__":
    CLI.run()
