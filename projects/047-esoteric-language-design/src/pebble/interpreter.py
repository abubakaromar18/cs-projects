"""Tree-walking interpreter for Pebble.

Machine model
-------------
* one data stack of unbounded Python integers
* 26 registers, a..z, all starting at 0
* a dictionary of words (user-defined subroutines, A..Z)
* an output stream and an input stream

Execution walks the AST directly. Loops and ifs recurse into their
bodies; word calls recurse into the word's body with a depth counter so
runaway recursion becomes a clean Pebble error instead of a Python crash.
"""

from __future__ import annotations

import io
import sys
from typing import Callable, TextIO

from . import ast
from .errors import PebbleRuntimeError
from .parser import parse


class Interpreter:
    def __init__(
        self,
        stdout: TextIO | None = None,
        stdin: TextIO | None = None,
        max_steps: int | None = None,
        max_depth: int = 256,
    ) -> None:
        self.out = stdout if stdout is not None else sys.stdout
        self.inp = stdin if stdin is not None else sys.stdin
        self.max_steps = max_steps
        self.max_depth = max_depth
        self.stack: list[int] = []
        self.registers: dict[str, int] = {chr(c): 0 for c in range(ord("a"), ord("z") + 1)}
        self.words: dict[str, ast.Define] = {}
        self.steps = 0
        self.depth = 0
        self._ops: dict[str, Callable[[ast.Op], None]] = self._build_op_table()

    # -- public API ---------------------------------------------------
    def run(self, program: ast.Program | str) -> None:
        if isinstance(program, str):
            program = parse(program, known_words=self.words)
        # Words are hoisted, so a word may be called before (textually)
        # it is defined. A REPL can also redefine words between runs.
        self.words.update(program.words)
        # Each nested Pebble construct costs a few Python frames.
        sys.setrecursionlimit(max(sys.getrecursionlimit(), self.max_depth * 12 + 1000))
        self._exec(program.body)

    # -- stack helpers ------------------------------------------------
    def _pop(self, node: ast.Node, n: int = 1) -> list[int]:
        if len(self.stack) < n:
            what = getattr(node, "symbol", None) or type(node).__name__
            raise PebbleRuntimeError(
                f"stack underflow: '{what}' needs {n} value(s), stack has {len(self.stack)}",
                node.line,
                node.col,
            )
        vals = self.stack[-n:]
        del self.stack[-n:]
        return vals

    def _peek(self, node: ast.Node) -> int:
        if not self.stack:
            raise PebbleRuntimeError("stack underflow: loop test on empty stack", node.line, node.col)
        return self.stack[-1]

    # -- the evaluator ------------------------------------------------
    def _exec(self, nodes: list[ast.Node]) -> None:
        for node in nodes:
            self._tick(node)

            if isinstance(node, ast.Push):
                self.stack.append(node.value)
            elif isinstance(node, ast.PushString):
                self.stack.append(0)
                self.stack.extend(ord(c) for c in reversed(node.text))
            elif isinstance(node, ast.Op):
                self._ops[node.symbol](node)
            elif isinstance(node, ast.Load):
                self.stack.append(self.registers[node.register])
            elif isinstance(node, ast.Store):
                (self.registers[node.register],) = self._pop(node)
            elif isinstance(node, ast.While):
                while self._peek(node) != 0:
                    self._exec(node.body)
                    self._tick(node)  # count iterations so even `[ ]` hits the limit
            elif isinstance(node, ast.If):
                (cond,) = self._pop(node)
                if cond != 0:
                    self._exec(node.body)
            elif isinstance(node, ast.Call):
                self._call(node)
            else:  # pragma: no cover - parser never produces anything else
                raise PebbleRuntimeError(f"unknown node {node!r}", node.line, node.col)

    def _tick(self, node: ast.Node) -> None:
        """Count one unit of work and enforce the optional step limit."""
        self.steps += 1
        if self.max_steps is not None and self.steps > self.max_steps:
            raise PebbleRuntimeError(
                f"step limit of {self.max_steps} exceeded (infinite loop?)", node.line, node.col
            )

    def _call(self, node: ast.Call) -> None:
        if node.word not in self.words:
            raise PebbleRuntimeError(f"undefined word {node.word}", node.line, node.col)
        if self.depth >= self.max_depth:
            raise PebbleRuntimeError(
                f"call depth limit of {self.max_depth} exceeded (runaway recursion?)",
                node.line,
                node.col,
            )
        self.depth += 1
        try:
            self._exec(self.words[node.word].body)
        finally:
            self.depth -= 1

    # -- instruction table --------------------------------------------
    def _build_op_table(self) -> dict[str, Callable[[ast.Op], None]]:
        push = self.stack.append

        def binary(fn):
            def op(node):
                a, b = self._pop(node, 2)
                push(fn(a, b, node))
            return op

        def div(a, b, node):
            if b == 0:
                raise PebbleRuntimeError("division by zero", node.line, node.col)
            return a // b

        def mod(a, b, node):
            if b == 0:
                raise PebbleRuntimeError("modulo by zero", node.line, node.col)
            return a % b

        def dup(node):
            (a,) = self._pop(node)
            push(a)
            push(a)

        def drop(node):
            self._pop(node)

        def swap(node):
            a, b = self._pop(node, 2)
            push(b)
            push(a)

        def rot(node):  # a b c -> b c a
            a, b, c = self._pop(node, 3)
            self.stack.extend((b, c, a))

        def over(node):  # a b -> a b a
            a, b = self._pop(node, 2)
            self.stack.extend((a, b, a))

        def logical_not(node):
            (a,) = self._pop(node)
            push(int(a == 0))

        def print_num(node):
            (a,) = self._pop(node)
            self.out.write(str(a))

        def print_char(node):
            (a,) = self._pop(node)
            if not 0 <= a <= 0x10FFFF:
                raise PebbleRuntimeError(f"{a} is not a valid character code", node.line, node.col)
            self.out.write(chr(a))

        def read_char(node):
            c = self.inp.read(1)
            push(ord(c) if c else -1)

        def read_num(node):
            # Skip leading whitespace, then read an optional '-' and digits.
            c = self.inp.read(1)
            while c and c.isspace():
                c = self.inp.read(1)
            if not c:
                push(-1)
                return
            text = ""
            if c == "-":
                text, c = "-", self.inp.read(1)
            while c and c.isdigit():
                text += c
                c = self.inp.read(1)
            if text in ("", "-"):
                raise PebbleRuntimeError("'&' expected a number on input", node.line, node.col)
            push(int(text))

        return {
            "+": binary(lambda a, b, _: a + b),
            "-": binary(lambda a, b, _: a - b),
            "*": binary(lambda a, b, _: a * b),
            "/": binary(div),
            "%": binary(mod),
            "=": binary(lambda a, b, _: int(a == b)),
            "<": binary(lambda a, b, _: int(a < b)),
            ">": binary(lambda a, b, _: int(a > b)),
            "!": logical_not,
            ":": dup,
            "$": drop,
            "\\": swap,
            "@": rot,
            "^": over,
            ".": print_num,
            ",": print_char,
            "?": read_char,
            "&": read_num,
        }


def run_source(source: str, stdin: str = "", max_steps: int | None = 1_000_000) -> str:
    """Convenience helper: run `source` with string input and return its output."""
    out = io.StringIO()
    Interpreter(stdout=out, stdin=io.StringIO(stdin), max_steps=max_steps).run(source)
    return out.getvalue()
