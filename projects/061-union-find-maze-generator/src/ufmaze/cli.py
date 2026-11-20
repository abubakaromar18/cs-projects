"""Command-line interface: ``ufmaze [options]``."""

from __future__ import annotations

import argparse
import sys
import time

from . import render, solver
from .maze import generate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ufmaze",
        description="Generate a perfect maze with Kruskal + union-find, then solve it.",
    )
    p.add_argument("-r", "--rows", type=int, default=10, help="number of rows (default 10)")
    p.add_argument("-c", "--cols", type=int, default=20, help="number of columns (default 20)")
    p.add_argument("-s", "--seed", type=int, help="random seed for reproducible mazes")
    p.add_argument("--solve", choices=["bfs", "astar"], help="draw the solution path")
    p.add_argument("--svg", metavar="FILE", help="also write an SVG drawing to FILE")
    p.add_argument("--animate", action="store_true",
                   help="print the maze after every wall removal (small mazes only)")
    p.add_argument("--stats", action="store_true", help="print generation/solve statistics")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.rows < 1 or args.cols < 1:
        print("ufmaze: rows and cols must be >= 1", file=sys.stderr)
        return 2

    step = None
    if args.animate:
        def step(m, a, b):  # noqa: E306 - small local callback
            print(render.to_ascii(m), end="\n\n")
            time.sleep(0.05)

    t0 = time.perf_counter()
    maze = generate(args.rows, args.cols, seed=args.seed, on_step=step)
    gen_ms = (time.perf_counter() - t0) * 1000

    path: list = []
    sol = None
    if args.solve:
        t1 = time.perf_counter()
        sol = (solver.bfs if args.solve == "bfs" else solver.astar)(maze)
        solve_ms = (time.perf_counter() - t1) * 1000
        path = sol.path

    print(render.to_ascii(maze, path))

    if args.svg:
        with open(args.svg, "w", encoding="utf-8") as fh:
            fh.write(render.to_svg(maze, path))
        print(f"wrote {args.svg}", file=sys.stderr)

    if args.stats:
        print(f"\ncells: {args.rows * args.cols}  passages: {len(maze.passages)}  "
              f"generated in {gen_ms:.2f} ms")
        if sol is not None:
            print(f"{args.solve}: path length {sol.length}, explored {sol.explored} cells, "
                  f"{solve_ms:.2f} ms")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
