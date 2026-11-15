"""Command-line entry point.

    colorpick                      launch the GUI
    colorpick gui "#3366ff"        launch the GUI with a starting color
    colorpick convert "hsl(210, 80%, 50%)"   print every format
    colorpick contrast "#333" white          WCAG contrast ratio
    colorpick harmony tomato                 color-wheel schemes
"""
from __future__ import annotations

import argparse
import sys

from .colors import contrast_ratio, harmonies, parse_color


def _color(text: str):
    try:
        return parse_color(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="colorpick", description="Pick and convert colors.")
    sub = p.add_subparsers(dest="cmd")
    g = sub.add_parser("gui", help="open the desktop picker (default)")
    g.add_argument("color", nargs="?", type=_color)
    c = sub.add_parser("convert", help="show a color in every format")
    c.add_argument("color", type=_color)
    k = sub.add_parser("contrast", help="WCAG contrast ratio of two colors")
    k.add_argument("fg", type=_color)
    k.add_argument("bg", type=_color)
    h = sub.add_parser("harmony", help="print color-wheel harmonies")
    h.add_argument("color", type=_color)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = sys.stdout
    if args.cmd == "convert":
        for name, text in args.color.formats().items():
            print(f"{name:<5} {text}", file=out)
    elif args.cmd == "contrast":
        r = contrast_ratio(args.fg, args.bg)
        verdict = "AAA" if r >= 7 else "AA" if r >= 4.5 else "AA (large text only)" if r >= 3 else "fails WCAG"
        print(f"{r:.2f}:1  {verdict}", file=out)
    elif args.cmd == "harmony":
        for name, cols in harmonies(args.color).items():
            print(f"{name:<20} " + " ".join(c.hex.upper() for c in cols), file=out)
    else:
        from .app import run  # import Tk lazily so the CLI works headless

        run(getattr(args, "color", None))
    return 0
