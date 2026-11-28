"""Command-line interface.

    sudoku solve FILE|- [--naive] [--stats] [--line]
    sudoku check FILE|-              # validity + uniqueness
    sudoku hint  FILE|-              # pencil marks after propagation
    sudoku generate [--seed N] [--givens N]
    sudoku bench DIR|FILE...         # naive vs propagation on each puzzle
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import board as B
from .generator import generate
from .solver import Result, candidates, count_solutions, solve, solve_naive


def _read(source: str) -> list[int]:
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return B.parse(text)


def _print_stats(res: Result, elapsed: float) -> None:
    s = res.stats
    print(
        f"nodes={s.nodes} guesses={s.guesses} backtracks={s.backtracks} "
        f"propagated={s.propagated} time={elapsed * 1000:.1f}ms"
    )


def cmd_solve(args: argparse.Namespace) -> int:
    puzzle = _read(args.puzzle)
    if not B.is_valid(puzzle):
        print("error: puzzle has conflicting givens", file=sys.stderr)
        return 2
    t0 = time.perf_counter()
    res = solve_naive(puzzle) if args.naive else solve(puzzle)
    elapsed = time.perf_counter() - t0
    if not res.solved:
        print("no solution", file=sys.stderr)
        return 1
    print(B.to_line(res.solution) if args.line else B.to_grid(res.solution))
    if args.stats:
        _print_stats(res, elapsed)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    puzzle = _read(args.puzzle)
    bad = B.conflicts(puzzle)
    if bad:
        for a, b in bad:
            print(f"conflict: r{a // 9 + 1}c{a % 9 + 1} and r{b // 9 + 1}c{b % 9 + 1} both {puzzle[a]}")
        return 2
    n = count_solutions(puzzle, limit=2)
    print({0: "unsolvable", 1: "unique solution"}.get(n, "multiple solutions"))
    return 0 if n == 1 else 1


def cmd_hint(args: argparse.Namespace) -> int:
    puzzle = _read(args.puzzle)
    marks = candidates(puzzle)
    if not marks:
        print("contradiction: puzzle cannot be solved", file=sys.stderr)
        return 1
    for r in range(9):
        cells = []
        for c in range(9):
            m = marks[r * 9 + c]
            cells.append("".join(map(str, sorted(m))).ljust(9))
        print(" ".join(cells))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    puzzle, solution = generate(seed=args.seed, min_givens=args.givens)
    print(B.to_grid(puzzle))
    print(f"\n{sum(1 for v in puzzle if v)} givens")
    if args.show_solution:
        print("\n" + B.to_grid(solution))
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    files: list[Path] = []
    for p in map(Path, args.paths):
        files.extend(sorted(p.glob("*.txt")) if p.is_dir() else [p])
    print(f"{'puzzle':<14}{'method':<14}{'nodes':>10}{'guesses':>10}{'ms':>10}")
    for f in files:
        puzzle = B.parse(f.read_text())
        for name, fn in (("naive", lambda p: solve_naive(p, max_nodes=args.limit)), ("propagation", solve)):
            t0 = time.perf_counter()
            res = fn(puzzle)
            ms = (time.perf_counter() - t0) * 1000
            nodes = f"{res.stats.nodes}" + ("" if res.solved else "+")
            print(f"{f.stem:<14}{name:<14}{nodes:>10}{res.stats.guesses:>10}{ms:>10.1f}")
    print("('+' = naive search hit the node limit)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sudoku", description="Sudoku solver with constraint propagation")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("solve", help="solve a puzzle")
    s.add_argument("puzzle", help="file path, or - for stdin")
    s.add_argument("--naive", action="store_true", help="use plain backtracking")
    s.add_argument("--stats", action="store_true", help="print search statistics")
    s.add_argument("--line", action="store_true", help="print as one 81-char line")
    s.set_defaults(func=cmd_solve)

    c = sub.add_parser("check", help="check validity and uniqueness")
    c.add_argument("puzzle")
    c.set_defaults(func=cmd_check)

    h = sub.add_parser("hint", help="show candidates after propagation")
    h.add_argument("puzzle")
    h.set_defaults(func=cmd_hint)

    g = sub.add_parser("generate", help="generate a unique-solution puzzle")
    g.add_argument("--seed", type=int)
    g.add_argument("--givens", type=int, default=26, help="stop removing at this many givens")
    g.add_argument("--show-solution", action="store_true")
    g.set_defaults(func=cmd_generate)

    b = sub.add_parser("bench", help="compare naive vs propagation")
    b.add_argument("paths", nargs="+")
    b.add_argument("--limit", type=int, default=200_000, help="node limit for naive search")
    b.set_defaults(func=cmd_bench)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (B.ParseError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
