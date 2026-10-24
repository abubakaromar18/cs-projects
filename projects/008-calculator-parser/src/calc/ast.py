"""Abstract syntax tree node definitions.

Nodes are immutable dataclasses. Each keeps the source position of the token
that created it so runtime errors can point back into the input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Number:
    value: float
    pos: int = 0


@dataclass(frozen=True)
class Name:
    ident: str
    pos: int = 0


@dataclass(frozen=True)
class UnaryOp:
    op: str          # "+" or "-"
    operand: "Node"
    pos: int = 0


@dataclass(frozen=True)
class BinaryOp:
    op: str          # "+", "-", "*", "/", "//", "%", "^"
    left: "Node"
    right: "Node"
    pos: int = 0


@dataclass(frozen=True)
class Factorial:
    operand: "Node"
    pos: int = 0


@dataclass(frozen=True)
class Call:
    func: str
    args: tuple["Node", ...]
    pos: int = 0


@dataclass(frozen=True)
class Assign:
    target: str
    value: "Node"
    pos: int = 0


Node = Union[Number, Name, UnaryOp, BinaryOp, Factorial, Call, Assign]


def _fmt_number(v: float) -> str:
    return str(int(v)) if v.is_integer() else repr(v)


def to_sexpr(node: Node) -> str:
    """Render a tree as a Lisp-style S-expression, e.g. (+ 1 (* 2 3)).

    Handy for tests and for the CLI's --ast flag: the nesting makes the
    parser's precedence and associativity decisions explicit.
    """
    match node:
        case Number(value=v):
            return _fmt_number(v)
        case Name(ident=name):
            return name
        case UnaryOp(op=op, operand=x):
            return f"(neg {to_sexpr(x)})" if op == "-" else f"(pos {to_sexpr(x)})"
        case BinaryOp(op=op, left=l, right=r):
            return f"({op} {to_sexpr(l)} {to_sexpr(r)})"
        case Factorial(operand=x):
            return f"(! {to_sexpr(x)})"
        case Call(func=f, args=args):
            inner = " ".join(to_sexpr(a) for a in args)
            return f"({f} {inner})" if inner else f"({f})"
        case Assign(target=t, value=v):
            return f"(= {t} {to_sexpr(v)})"
    raise TypeError(f"unknown node {node!r}")
