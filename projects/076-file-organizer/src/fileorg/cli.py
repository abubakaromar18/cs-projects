"""Command-line interface: ``fileorg organize`` and ``fileorg undo``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .executor import apply_plan, undo
from .planner import Mode, plan_moves
from .rules import load_rules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fileorg",
        description="Sort files into folders by type and/or date.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    org = sub.add_parser("organize", help="organize a directory")
    org.add_argument("directory", type=Path)
    org.add_argument("--by", choices=[m.value for m in Mode], default=Mode.TYPE.value,
                     help="grouping: type (default), date (YYYY/MM), or type-date")
    org.add_argument("-n", "--dry-run", action="store_true",
                     help="show what would happen without moving anything")
    org.add_argument("-r", "--recursive", action="store_true",
                     help="also organize files in subdirectories")
    org.add_argument("--include-hidden", action="store_true",
                     help="include dotfiles and hidden folders")
    org.add_argument("--rules", type=Path, metavar="FILE",
                     help="JSON file mapping category -> [extensions]")
    org.add_argument("-q", "--quiet", action="store_true", help="only print the summary")

    und = sub.add_parser("undo", help="reverse the most recent organize run")
    und.add_argument("directory", type=Path)
    return parser


def _organize(args: argparse.Namespace) -> int:
    rules = load_rules(args.rules)
    plan = plan_moves(args.directory, rules=rules, mode=args.by,
                      recursive=args.recursive, include_hidden=args.include_hidden)
    if not plan.moves:
        print("Nothing to organize.")
        return 0

    if not args.quiet:
        for move in plan.moves:
            src, dst = move.relative(plan.root)
            print(f"  {src}  ->  {dst}")
    for path, reason in plan.skipped:
        print(f"  skipped {path} ({reason})", file=sys.stderr)

    counts = ", ".join(f"{folder}: {n}" for folder, n in plan.summary().items())
    if args.dry_run:
        print(f"Dry run: would move {len(plan.moves)} file(s) ({counts}).")
        return 0

    result = apply_plan(plan)
    for src, err in result.errors:
        print(f"  error moving {src}: {err}", file=sys.stderr)
    print(f"Moved {result.moved} file(s) ({counts}).")
    if result.moved:
        print(f"Undo with: fileorg undo {args.directory}")
    return 1 if result.errors else 0


def _undo(args: argparse.Namespace) -> int:
    result = undo(args.directory)
    for dst, err in result.errors:
        print(f"  error restoring {dst}: {err}", file=sys.stderr)
    if result.moved == 0 and not result.errors:
        print("Nothing to undo.")
    else:
        print(f"Restored {result.moved} file(s).")
    return 1 if result.errors else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "organize":
            return _organize(args)
        return _undo(args)
    except (NotADirectoryError, FileNotFoundError) as exc:
        print(f"fileorg: no such directory or file: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"fileorg: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
