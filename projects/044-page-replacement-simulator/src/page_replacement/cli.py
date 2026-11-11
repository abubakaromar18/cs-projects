"""Command-line interface: ``pagesim {trace,compare,sweep,belady,list}``."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import analysis, refstrings, render
from .policies import POLICIES
from .simulator import compare, simulate


def _add_workload(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("workload (default: the textbook string)")
    src = g.add_mutually_exclusive_group()
    src.add_argument("-r", "--refs", help='explicit string, e.g. "7 0 1 2 0 3"')
    src.add_argument("--preset", choices=sorted(refstrings.PRESETS))
    src.add_argument(
        "--gen", choices=["uniform", "locality", "loop"], help="synthetic workload"
    )
    g.add_argument("-n", "--length", type=int, default=200, help="generated length")
    g.add_argument("-p", "--pages", type=int, default=10, help="distinct pages")
    g.add_argument("--working-set", type=int, default=4, help="locality: WS size")
    g.add_argument("--seed", type=int, default=None, help="RNG seed")


def _workload(args: argparse.Namespace) -> tuple[int, ...]:
    if args.refs:
        return refstrings.parse(args.refs)
    if args.preset:
        return refstrings.PRESETS[args.preset]
    if args.gen == "uniform":
        return refstrings.uniform(args.length, args.pages, args.seed)
    if args.gen == "locality":
        return refstrings.locality(
            args.length, args.pages, args.working_set, seed=args.seed
        )
    if args.gen == "loop":
        return refstrings.loop(args.length, args.pages)
    return refstrings.TEXTBOOK


def _algos(value: str) -> list[str]:
    names = [a.strip().lower() for a in value.split(",") if a.strip()]
    bad = [a for a in names if a not in POLICIES]
    if bad or not names:
        raise argparse.ArgumentTypeError(
            f"unknown algorithm(s) {bad}; choose from {', '.join(POLICIES)}"
        )
    return names


def _frame_range(value: str) -> range:
    lo, _, hi = value.partition("-")
    lo_i, hi_i = int(lo), int(hi or lo)
    if lo_i < 1 or hi_i < lo_i:
        raise argparse.ArgumentTypeError("use a range like 1-8 with 1 <= lo <= hi")
    return range(lo_i, hi_i + 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pagesim", description="Simulate and compare page replacement policies."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("trace", help="step through one algorithm")
    p.add_argument("-a", "--algorithm", default="lru", choices=list(POLICIES))
    p.add_argument("-f", "--frames", type=int, default=3)
    p.add_argument("--steps", action="store_true", help="one line per reference")
    _add_workload(p)

    p = sub.add_parser("compare", help="all algorithms, one frame count")
    p.add_argument("-f", "--frames", type=int, default=3)
    p.add_argument("-a", "--algorithms", type=_algos, default=list(POLICIES))
    _add_workload(p)

    p = sub.add_parser("sweep", help="fault curve across frame counts")
    p.add_argument("-F", "--frame-range", type=_frame_range, default=range(1, 8))
    p.add_argument("-a", "--algorithms", type=_algos, default=list(POLICIES))
    p.add_argument("--chart", action="store_true", help="draw ASCII bars")
    _add_workload(p)

    p = sub.add_parser("belady", help="demonstrate / search for Belady's anomaly")
    p.add_argument("-a", "--algorithm", default="fifo", choices=list(POLICIES))
    p.add_argument("--search", action="store_true", help="random search for one")
    p.add_argument("--tries", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=None)

    sub.add_parser("list", help="list algorithms")
    return parser


def _cmd_belady(args, out) -> int:
    if args.search:
        found = analysis.search_belady(args.algorithm, tries=args.tries, seed=args.seed)
        if found is None:
            print(f"No anomaly for {args.algorithm} in {args.tries} tries.", file=out)
            if args.algorithm in ("lru", "opt"):
                print("(Expected: LRU and OPT are stack algorithms.)", file=out)
            return 1
        refs, a = found
    else:
        refs = refstrings.BELADY
        found = analysis.find_anomalies(
            analysis.sweep(refs, [args.algorithm], range(1, 6))
        )
        if not found:
            print(f"{args.algorithm} shows no anomaly on {refs}.", file=out)
            return 1
        a = found[0]
    print("refs: " + " ".join(map(str, refs)), file=out)
    print(
        f"{a.algorithm.upper()}: {a.frames} frames -> {a.faults} faults, "
        f"but {a.more_frames} frames -> {a.more_faults} faults (Belady's anomaly)",
        file=out,
    )
    for k in (a.frames, a.more_frames):
        print("\n" + render.trace_grid(simulate(refs, k, a.algorithm)), file=out)
    return 0


def main(argv: Sequence[str] | None = None, out=None) -> int:
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "list":
            for name, cls in POLICIES.items():
                print(f"{name:<6} {cls.description}", file=out)
            return 0
        if args.cmd == "belady":
            return _cmd_belady(args, out)

        refs = _workload(args)
        if args.cmd == "trace":
            result = simulate(refs, args.frames, args.algorithm)
            text = render.trace_steps(result) if args.steps else render.trace_grid(result)
            print(text, file=out)
            if args.steps:
                print(f"{result.faults} faults / {len(refs)} refs", file=out)
        elif args.cmd == "compare":
            print(f"{len(refs)} refs, {len(set(refs))} distinct pages, "
                  f"{args.frames} frames\n", file=out)
            print(render.comparison_table(compare(refs, args.frames, args.algorithms)),
                  file=out)
        elif args.cmd == "sweep":
            curves = analysis.sweep(refs, args.algorithms, args.frame_range)
            print(render.bar_chart(curves) if args.chart else render.sweep_table(curves),
                  file=out)
            for a in analysis.find_anomalies(curves):
                print(f"! Belady's anomaly: {a.algorithm} {a.frames}->{a.more_frames} "
                      f"frames went {a.faults}->{a.more_faults} faults", file=out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
