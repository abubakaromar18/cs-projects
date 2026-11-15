"""CLI: ``python -m analytics [QUERY ...] [--db FILE]``.

With no query names, runs every query and prints a plain-text table for each.
"""

from __future__ import annotations

import argparse

from .db import build_database, list_queries, load_query, run_query


def format_table(columns: list[str], rows: list[tuple]) -> str:
    """Render rows as a simple aligned text table."""
    cells = [[("NULL" if v is None else str(v)) for v in row] for row in rows]
    widths = [max(len(c), *(len(r[i]) for r in cells)) if cells else len(c) for i, c in enumerate(columns)]
    line = lambda vals: " | ".join(v.ljust(w) for v, w in zip(vals, widths))  # noqa: E731
    out = [line(columns), "-+-".join("-" * w for w in widths)]
    out += [line(r) for r in cells]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SQL analyses on the Palmer Penguins dataset.")
    parser.add_argument("queries", nargs="*", help="query names or numbers (default: all)")
    parser.add_argument("--db", default=":memory:", help="write the SQLite database to this file")
    parser.add_argument("--list", action="store_true", help="list available queries and exit")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(list_queries()))
        return 0

    conn = build_database(args.db)
    for name in args.queries or list_queries():
        title = load_query(name).splitlines()[0].lstrip("- ").strip()
        print(f"\n=== {title} ===")
        print(format_table(*run_query(conn, name)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
