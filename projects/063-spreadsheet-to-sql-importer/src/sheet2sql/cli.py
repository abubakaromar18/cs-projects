"""Command-line interface: ``sheet2sql FILE [FILE ...] --db out.db``."""

from __future__ import annotations

import argparse
import sqlite3
import sys

from . import __version__
from .loader import IF_EXISTS, ImportFailure, describe, infer_schema, load_table
from .readers import ReaderError, read_any


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sheet2sql",
        description="Infer column types and load CSV/XLSX files into SQLite.",
    )
    p.add_argument("files", nargs="+", help="CSV, TSV or XLSX files")
    p.add_argument("--db", default=":memory:", help="SQLite database path (default: in-memory)")
    p.add_argument("-t", "--table", help="table name (single-table input only)")
    p.add_argument("--sheet", help="only import this worksheet from XLSX files")
    p.add_argument("-d", "--delimiter", help="CSV delimiter (default: sniffed)")
    p.add_argument("--if-exists", choices=IF_EXISTS, default="fail",
                   help="what to do when the table exists (default: fail)")
    p.add_argument("--sample", type=int, metavar="N",
                   help="infer types from the first N rows only (default: all rows)")
    p.add_argument("--strict", action="store_true",
                   help="abort if a value does not match its inferred type")
    p.add_argument("--no-pk", action="store_true", help="do not detect a primary key")
    p.add_argument("--dry-run", action="store_true",
                   help="print the CREATE TABLE statements without loading")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tables = [t for f in args.files for t in read_any(f, args.sheet, args.delimiter)]
    except ReaderError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.table and len(tables) > 1:
        print("error: --table needs exactly one input table", file=sys.stderr)
        return 2

    if args.dry_run:
        for t in tables:
            schema = infer_schema(t, args.sample, not args.no_pk)
            if args.table:
                schema.table = args.table
            print(schema.create_sql())
        return 0

    conn = sqlite3.connect(args.db)
    try:
        for t in tables:
            result = load_table(
                conn, t,
                table_name=args.table,
                if_exists=args.if_exists,
                sample=args.sample,
                strict=args.strict,
                detect_pk=not args.no_pk,
            )
            print(describe(result))
            for w in result.warnings[:5]:
                print(f"  warning: {w}", file=sys.stderr)
            if len(result.warnings) > 5:
                print(f"  ... {len(result.warnings) - 5} more warning(s)", file=sys.stderr)
    except ImportFailure as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
