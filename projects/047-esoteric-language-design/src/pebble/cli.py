"""Command-line front end: run files, inline code, dump tokens/AST, or start a REPL."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .ast import dump
from .errors import PebbleError
from .interpreter import Interpreter
from .lexer import tokenize
from .parser import parse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pebble", description="Run Pebble programs.")
    p.add_argument("file", nargs="?", help="a .pbl source file (omit for the REPL)")
    p.add_argument("-e", "--eval", metavar="CODE", help="run CODE instead of a file")
    p.add_argument("--tokens", action="store_true", help="print the token stream and exit")
    p.add_argument("--ast", action="store_true", help="print the syntax tree and exit")
    p.add_argument("--stack", action="store_true", help="print the final stack after running")
    p.add_argument("--max-steps", type=int, default=None, help="abort after N instructions")
    p.add_argument("--version", action="version", version=f"pebble {__version__}")
    return p


def repl(interp: Interpreter) -> int:
    """Read-eval-print loop. State (stack, registers, words) persists between lines."""
    print(f"pebble {__version__} — type code, 'quit' to exit. Stack is shown after each line.")
    while True:
        try:
            line = input("pebble> ")
        except EOFError:
            print()
            return 0
        if line.strip() in ("quit", "exit"):
            return 0
        try:
            interp.run(line)
        except PebbleError as e:
            print(e, file=sys.stderr)
        interp.out.flush()
        print(f"\n  stack: {interp.stack}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.eval is not None:
        source, name = args.eval, "<eval>"
    elif args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                source, name = fh.read(), args.file
        except OSError as e:
            print(f"pebble: cannot read {args.file}: {e.strerror}", file=sys.stderr)
            return 2
    else:
        return repl(Interpreter(max_steps=args.max_steps))

    try:
        if args.tokens:
            for tok in tokenize(source):
                print(repr(tok))
            return 0
        program = parse(source)
        if args.ast:
            print(dump(program.body))
            for word in program.words.values():
                print(dump([word]))
            return 0
        interp = Interpreter(max_steps=args.max_steps)
        interp.run(program)
    except PebbleError as e:
        sys.stdout.flush()
        print(f"{name}: {e}", file=sys.stderr)
        return 1
    if args.stack:
        print(f"\nstack: {interp.stack}")
    return 0
