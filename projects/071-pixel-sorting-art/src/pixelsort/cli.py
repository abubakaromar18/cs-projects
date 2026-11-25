"""Command-line interface: `pixelsort INPUT -o OUTPUT [options]`."""

from __future__ import annotations

import argparse
import os
import sys

from PIL import Image

from .generate import GENERATORS
from .intervals import INTERVALS
from .keys import KEYS
from .sorter import SortConfig, sort_image


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pixelsort", description="Glitch-art pixel sorter")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("input", nargs="?", help="input image path")
    src.add_argument("--demo", choices=sorted(GENERATORS), help="use a generated source image")
    p.add_argument("-o", "--output", required=True, help="output image path")
    p.add_argument("-k", "--key", default="lightness", choices=sorted(KEYS))
    p.add_argument("-i", "--interval", default="threshold", choices=sorted(INTERVALS))
    p.add_argument("-a", "--angle", type=float, default=0.0, help="sort direction in degrees")
    p.add_argument("-r", "--reverse", action="store_true", help="sort descending")
    p.add_argument("--lower", type=float, default=0.25)
    p.add_argument("--upper", type=float, default=0.8)
    p.add_argument("--edge-threshold", type=float, default=0.1)
    p.add_argument("--mean-length", type=int, default=40)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--save-source", help="also save the (generated) source image here")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.demo:
        img = GENERATORS[args.demo](seed=args.seed or 0)
    else:
        img = Image.open(args.input)
    for path in (args.output, args.save_source):
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if args.save_source:
        img.save(args.save_source)
    cfg = SortConfig(key=args.key, interval=args.interval, angle=args.angle, reverse=args.reverse,
                     lower=args.lower, upper=args.upper, edge_threshold=args.edge_threshold,
                     mean_length=args.mean_length, seed=args.seed)
    try:
        out = sort_image(img, cfg)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out.save(args.output)
    print(f"wrote {args.output} ({out.size[0]}x{out.size[1]}, key={cfg.key}, interval={cfg.interval}, angle={cfg.angle})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
