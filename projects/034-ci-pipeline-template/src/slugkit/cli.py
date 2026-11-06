"""Command-line entry point: ``slugkit "Some Title"``."""

from __future__ import annotations

import argparse
import sys

from slugkit.core import slugify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slugkit", description="Turn text into URL slugs.")
    parser.add_argument("text", nargs="+", help="text to slugify")
    parser.add_argument("-s", "--separator", default="-")
    parser.add_argument("-m", "--max-length", type=int, default=None)
    args = parser.parse_args(argv)
    try:
        print(slugify(" ".join(args.text), args.separator, args.max_length))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
