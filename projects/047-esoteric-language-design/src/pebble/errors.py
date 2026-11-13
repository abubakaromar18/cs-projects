"""Error types shared by every stage of the Pebble pipeline."""

from __future__ import annotations


class PebbleError(Exception):
    """Base class: anything that goes wrong while running a Pebble program."""

    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        self.message = message
        self.line = line
        self.col = col
        where = f" at {line}:{col}" if line is not None else ""
        super().__init__(f"{self.kind}{where}: {message}")

    kind = "error"


class PebbleSyntaxError(PebbleError):
    """Raised by the lexer or parser for malformed source."""

    kind = "syntax error"


class PebbleRuntimeError(PebbleError):
    """Raised by the interpreter (stack underflow, divide by zero, ...)."""

    kind = "runtime error"
