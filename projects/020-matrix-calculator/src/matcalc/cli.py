"""Command-line interface: ``matcalc <operation> MATRIX [options]``.

A matrix argument can be literal text (``"1 2; 3 4"``), ``@path/to/file``
to read it from a file, or ``-`` to read it from standard input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .matrix import Matrix, fmt
from .operations import (
    SingularMatrixError,
    determinant,
    determinant_cofactor,
    inverse_with_steps,
    rref,
    solve,
)
from .parser import parse_matrix


def load(arg: str) -> Matrix:
    if arg == "-":
        return parse_matrix(sys.stdin.read())
    if arg.startswith("@"):
        return parse_matrix(Path(arg[1:]).read_text(encoding="utf-8"))
    return parse_matrix(arg)


def _print_steps(log, enabled: bool) -> None:
    if enabled:
        print(log.render())
        print()


def cmd_det(args) -> None:
    m = load(args.matrix)
    result = determinant(m, steps=args.steps)
    _print_steps(result.steps, args.steps)
    if args.steps:
        print(result.explanation)
    if args.check:
        cof = determinant_cofactor(m)
        status = "agrees" if cof == result.value else "DISAGREES"
        print(f"Cofactor expansion gives {fmt(cof)} ({status})")
    print(f"det = {fmt(result.value)}")


def cmd_inv(args) -> None:
    m = load(args.matrix)
    result = inverse_with_steps(m, steps=args.steps)
    _print_steps(result.steps, args.steps)
    print("A^-1 =")
    print(result.matrix)
    if args.check:
        ok = m @ result.matrix == Matrix.identity(m.rows)
        print(f"Check A * A^-1 == I: {'yes' if ok else 'NO'}")


def cmd_rref(args) -> None:
    result = rref(load(args.matrix), steps=args.steps)
    _print_steps(result.steps, args.steps)
    print("RREF =")
    print(result.matrix)
    print(f"rank = {result.rank}; pivot columns = {[p + 1 for p in result.pivots]}")


def cmd_rank(args) -> None:
    print(rref(load(args.matrix), steps=False).rank)


def cmd_solve(args) -> None:
    a, b = load(args.a), load(args.b)
    if b.rows == 1 and b.cols == a.rows:  # accept "1 2 3" as a column vector
        b = b.transpose()
    sol = solve(a, b, steps=args.steps)
    _print_steps(sol.rref.steps, args.steps)
    print(sol.describe())


def cmd_mul(args) -> None:
    print(load(args.a) @ load(args.b))


def cmd_transpose(args) -> None:
    print(load(args.matrix).transpose())


def cmd_pow(args) -> None:
    print(load(args.matrix) ** args.n)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="matcalc",
        description="Exact matrix calculator with step-by-step row reduction.",
        epilog='Example: matcalc det "2 1 -1; -3 -1 2; -2 1 2" --steps',
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def with_matrix(name, func, help_text, check=False):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("matrix", help='matrix text, @file or "-" for stdin')
        sp.add_argument("-s", "--steps", action="store_true", help="show every row operation")
        if check:
            sp.add_argument("--check", action="store_true", help="verify the answer independently")
        sp.set_defaults(func=func)
        return sp

    with_matrix("det", cmd_det, "determinant", check=True)
    with_matrix("inv", cmd_inv, "inverse via Gauss-Jordan on [A | I]", check=True)
    with_matrix("rref", cmd_rref, "reduced row echelon form, rank and pivots")
    with_matrix("rank", cmd_rank, "rank only")
    with_matrix("transpose", cmd_transpose, "transpose")
    pw = with_matrix("pow", cmd_pow, "integer power (negative uses the inverse)")
    pw.add_argument("n", type=int)

    sp = sub.add_parser("solve", help="solve Ax = b")
    sp.add_argument("a")
    sp.add_argument("b")
    sp.add_argument("-s", "--steps", action="store_true")
    sp.set_defaults(func=cmd_solve)

    sp = sub.add_parser("mul", help="matrix product A @ B")
    sp.add_argument("a")
    sp.add_argument("b")
    sp.set_defaults(func=cmd_mul)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except SingularMatrixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
