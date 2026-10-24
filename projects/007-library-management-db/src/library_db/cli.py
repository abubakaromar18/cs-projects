"""Command-line front end: ``library-db [--db FILE] <command> ...``."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any, Sequence

from . import db
from .isbn import InvalidISBN
from .library import Library, LibraryError
from .seed import is_empty, seed


def format_table(rows: Sequence[dict[str, Any]], columns: Sequence[str] | None = None) -> str:
    """Render rows as a plain-text table with left-aligned columns."""
    if not rows:
        return "(no rows)"
    columns = list(columns or rows[0].keys())
    cells = [[("" if r.get(c) is None else str(r.get(c))) for c in columns] for r in rows]
    widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(columns)]
    line = lambda vals: "  ".join(v.ljust(w) for v, w in zip(vals, widths)).rstrip()  # noqa: E731
    out = [line(columns), line(["-" * w for w in widths])]
    out += [line(row) for row in cells]
    return "\n".join(out)


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="library-db", description="Small library management system on SQLite.")
    p.add_argument("--db", default=str(db.DEFAULT_DB_PATH), help="database file (default: library.db)")
    p.add_argument("--today", help="override today's date (YYYY-MM-DD), handy for demos")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the schema")
    s = sub.add_parser("seed", help="load sample data into an empty database")
    s.add_argument("--force", action="store_true", help="seed even if books already exist")

    s = sub.add_parser("add-book", help="add a book")
    s.add_argument("isbn")
    s.add_argument("title")
    s.add_argument("-a", "--author", action="append", required=True, help="repeat for each author")
    s.add_argument("-p", "--publisher")
    s.add_argument("-y", "--year", type=int)
    s.add_argument("-g", "--genre", action="append", default=[])

    s = sub.add_parser("add-copy", help="add a physical copy of a book")
    s.add_argument("isbn")
    s.add_argument("barcode")

    s = sub.add_parser("add-member", help="register a member")
    s.add_argument("name")
    s.add_argument("email")

    s = sub.add_parser("checkout", help="lend a copy to a member")
    s.add_argument("barcode")
    s.add_argument("email")
    s = sub.add_parser("return", help="return a copy")
    s.add_argument("barcode")
    s = sub.add_parser("renew", help="renew a loan")
    s.add_argument("barcode")

    sub.add_parser("catalog", help="list all books with availability")
    s = sub.add_parser("search", help="search title, author, genre or ISBN")
    s.add_argument("text")
    sub.add_parser("overdue", help="overdue loans with fines")
    s = sub.add_parser("popular", help="most borrowed books")
    s.add_argument("-n", type=int, default=10)
    sub.add_parser("authors", help="per-author totals")
    s = sub.add_parser("history", help="a member's loan history")
    s.add_argument("email")
    sub.add_parser("stats", help="row counts")
    s = sub.add_parser("sql", help="run a read-only SQL query")
    s.add_argument("query")
    return p


def run(args: argparse.Namespace, lib: Library) -> str:
    t = args.today
    match args.cmd:
        case "init":
            return f"schema ready in {args.db}"
        case "seed":
            if not is_empty(lib) and not args.force:
                return "database already has books; use --force to seed anyway"
            seed(lib)
            return "seeded: " + ", ".join(f"{k}={v}" for k, v in lib.stats().items())
        case "add-book":
            bid = lib.add_book(args.isbn, args.title, args.author, args.publisher, args.year, args.genre)
            return f"added book #{bid}"
        case "add-copy":
            return f"added copy #{lib.add_copy(args.isbn, args.barcode, t)}"
        case "add-member":
            return f"added member #{lib.add_member(args.name, args.email, t)}"
        case "checkout":
            loan = lib.checkout(args.barcode, args.email, t)
            return f"loan #{loan['loan_id']}: {args.barcode} -> {args.email}, due {loan['due_on']}"
        case "return":
            r = lib.return_copy(args.barcode, t)
            msg = f"returned {args.barcode}"
            if r["days_late"]:
                msg += f", {r['days_late']} day(s) late, fine {money(r['fine_cents'])}"
            return msg
        case "renew":
            return f"renewed {args.barcode}, now due {lib.renew(args.barcode, t)['due_on']}"
        case "catalog":
            return format_table(lib.catalog(), ["isbn", "title", "authors", "published_year",
                                                "available_copies", "total_copies"])
        case "search":
            return format_table(lib.search(args.text), ["isbn", "title", "authors", "available_copies"])
        case "overdue":
            rows = lib.overdue(t)
            for r in rows:
                r["fine"] = money(r.pop("fine_cents"))
            return format_table(rows)
        case "popular":
            return format_table(lib.popular(args.n))
        case "authors":
            return format_table(lib.author_report())
        case "history":
            return format_table(lib.member_history(args.email))
        case "stats":
            return "\n".join(f"{k:12} {v}" for k, v in lib.stats().items())
        case "sql":
            return format_table(run_readonly(args.db, args.query))
    raise AssertionError(args.cmd)


def run_readonly(path: str, query: str) -> list[dict[str, Any]]:
    """Execute ad-hoc SQL on a read-only connection (``mode=ro`` URI), so a
    typo'd DELETE can't damage the data."""
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query).fetchall()]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = db.connect(args.db)
    try:
        print(run(args, Library(conn)))
        return 0
    except (LibraryError, InvalidISBN, sqlite3.Error, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
