"""Error types shared by the lexer, parser and evaluator.

Every error carries the character offset where it happened so the CLI can
draw a caret under the offending part of the input.
"""

from __future__ import annotations


class CalcError(Exception):
    """Base class for all calculator errors."""

    def __init__(self, message: str, pos: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.pos = pos

    def render(self, source: str) -> str:
        """Return a human-friendly message with a caret pointing at `pos`."""
        kind = type(self).__name__.replace("Error", " error").strip()
        if self.pos is None:
            return f"{kind}: {self.message}"
        caret = " " * self.pos + "^"
        return f"{source}\n{caret}\n{kind}: {self.message}"


class LexError(CalcError):
    """Raised when the input contains a character we can't tokenize."""


class ParseError(CalcError):
    """Raised when the token stream doesn't match the grammar."""


class EvalError(CalcError):
    """Raised for runtime problems: division by zero, unknown names, ..."""
