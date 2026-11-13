"""Abstract syntax tree for Pebble.

The tree is tiny: a program is a list of nodes, and only loops, ifs and
word definitions contain nested bodies. Every node remembers where it
came from so the interpreter can report runtime errors by position.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    line: int
    col: int


@dataclass
class Push(Node):
    """Push one integer (number and 'c literals)."""

    value: int


@dataclass
class PushString(Node):
    """Push a zero-terminated string so its first character ends up on top.

    "hi" leaves the stack as  ... 0 'i 'h   — perfect for a print loop
    like  [,]$  that prints characters until it reaches the 0.
    """

    text: str


@dataclass
class Op(Node):
    symbol: str


@dataclass
class Load(Node):
    register: str


@dataclass
class Store(Node):
    register: str


@dataclass
class Call(Node):
    word: str


@dataclass
class While(Node):
    """[ body ] — run body while the top of stack is non-zero (peeked, not popped)."""

    body: list[Node] = field(default_factory=list)


@dataclass
class If(Node):
    """{ body } — pop a value; run body once if it was non-zero."""

    body: list[Node] = field(default_factory=list)


@dataclass
class Define(Node):
    """(F body) — define word F. Definitions are hoisted before execution."""

    word: str
    body: list[Node] = field(default_factory=list)


@dataclass
class Program:
    body: list[Node]
    words: dict[str, Define]


def dump(nodes: list[Node], indent: int = 0) -> str:
    """Pretty-print a node list as an indented outline (used by --ast)."""
    pad = "  " * indent
    lines = []
    for n in nodes:
        if isinstance(n, (While, If, Define)):
            label = type(n).__name__ + (f" {n.word}" if isinstance(n, Define) else "")
            lines.append(f"{pad}{label}")
            inner = dump(n.body, indent + 1)
            if inner:
                lines.append(inner)
        elif isinstance(n, Push):
            lines.append(f"{pad}Push {n.value}")
        elif isinstance(n, PushString):
            lines.append(f"{pad}PushString {n.text!r}")
        elif isinstance(n, Op):
            lines.append(f"{pad}Op {n.symbol}")
        elif isinstance(n, Load):
            lines.append(f"{pad}Load {n.register}")
        elif isinstance(n, Store):
            lines.append(f"{pad}Store {n.register}")
        elif isinstance(n, Call):
            lines.append(f"{pad}Call {n.word}")
    return "\n".join(lines)
