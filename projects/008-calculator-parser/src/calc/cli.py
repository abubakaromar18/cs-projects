"""Command-line entry point: one-shot evaluation or an interactive REPL."""

from __future__ import annotations

import argparse
import sys

from .ast import to_sexpr
from .errors import CalcError, EvalError
from .evaluator import BUILTINS, CONSTANTS, Evaluator, format_number
from .lexer import tokenize
from .parser import parse

HELP = f"""Operators : + - * / // % ^ (or **)  !  ( )  and  name = expr
Functions : {', '.join(sorted(BUILTINS))}
Constants : {', '.join(sorted(CONSTANTS))}, plus `ans` (last result)
Commands  : :ast EXPR   :tokens EXPR   :vars   :help   :quit"""


def run_line(ev: Evaluator, line: str, show_ast: bool = False) -> str:
    """Process one REPL line and return the text to print."""
    line = line.strip()
    if line in (":help", "help"):
        return HELP
    if line == ":vars":
        if not ev.variables:
            return "(no variables)"
        return "\n".join(f"{k} = {format_number(v)}" for k, v in sorted(ev.variables.items()))
    if line.startswith(":tokens"):
        src = line[len(":tokens"):].strip()
        return " ".join(f"{t.type.name}({t.text})" if t.text else t.type.name for t in tokenize(src))
    if line.startswith(":ast"):
        try:
            return to_sexpr(parse(line[len(":ast"):].strip()))
        except RecursionError:
            raise EvalError("expression too long to print", 0) from None

    result = format_number(ev.evaluate(line))
    if show_ast:
        return f"{to_sexpr(parse(line))}\n{result}"
    return result


def repl(ev: Evaluator, show_ast: bool) -> int:
    print("calc — type :help for help, :quit to exit")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() in (":quit", ":q", "exit", "quit"):
            return 0
        if not line.strip():
            continue
        try:
            print(run_line(ev, line, show_ast))
        except CalcError as err:
            # Echo the line with a caret under the error position.
            print(err.render(line.strip()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="calc", description="Recursive descent calculator")
    ap.add_argument("expression", nargs="*", help="expression to evaluate (omit for a REPL)")
    ap.add_argument("--ast", action="store_true", help="also print the parse tree")
    args = ap.parse_args(argv)

    ev = Evaluator()
    if not args.expression:
        return repl(ev, args.ast)

    source = " ".join(args.expression)
    try:
        print(run_line(ev, source, args.ast))
    except CalcError as err:
        print(err.render(source.strip()), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
