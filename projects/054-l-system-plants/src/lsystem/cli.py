"""Command-line interface: ``lsystem fern -o fern.svg``."""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections import Counter

from .grammar import GrammarError, LSystem, parse_rules
from .presets import PRESETS
from .render import to_svg
from .turtle import TurtleConfig, interpret


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lsystem", description="Grow plants from L-system grammars.")
    p.add_argument("preset", nargs="?", help=f"one of: {', '.join(PRESETS)}")
    p.add_argument("--list", action="store_true", help="list presets and exit")
    p.add_argument("--axiom", help="custom axiom (use with --rule)")
    p.add_argument("--rule", action="append", default=[],
                   help="custom rule X=succ or X=0.5:a|0.5:b (repeatable)")
    p.add_argument("-n", "--iterations", type=int, help="rewriting steps")
    p.add_argument("-a", "--angle", type=float, help="turn angle in degrees")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for stochastic rules")
    p.add_argument("--size", type=int, default=800, help="SVG size in px")
    p.add_argument("-o", "--output", help="write SVG here (default: stdout)")
    p.add_argument("--stats", action="store_true", help="print string stats instead of SVG")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        for name, pr in PRESETS.items():
            print(f"{name:14} {pr.description}")
        return 0

    try:
        if args.axiom:
            system = LSystem(args.axiom, parse_rules(args.rule))
            iterations = args.iterations if args.iterations is not None else 4
            cfg = TurtleConfig()
        elif args.preset in PRESETS:
            pr = PRESETS[args.preset]
            system, iterations, cfg = pr.lsystem(), pr.iterations, pr.turtle
            if args.iterations is not None:
                iterations = args.iterations
        else:
            print(f"error: give a preset ({', '.join(PRESETS)}) or --axiom", file=sys.stderr)
            return 2

        if args.angle is not None:
            cfg = dataclasses.replace(cfg, angle=args.angle)
        cfg = dataclasses.replace(cfg, seed=args.seed)

        text = system.generate(iterations, seed=args.seed)
    except GrammarError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    segments = interpret(text, cfg)

    if args.stats:
        counts = Counter(text)
        top = ", ".join(f"{c}:{n}" for c, n in counts.most_common(6))
        print(f"iterations: {iterations}\nlength:     {len(text)}\n"
              f"segments:   {len(segments)}\nsymbols:    {top}")
        return 0

    svg = to_svg(segments, size=args.size)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {args.output} ({len(segments)} segments)", file=sys.stderr)
    else:
        sys.stdout.write(svg)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
