"""Lexer: turns Pebble source text into a flat list of tokens.

Pebble is a stack language where almost every token is one character.
The lexer's job is mostly to group the few multi-character forms
(numbers, strings, char literals, register names, comments) and to
attach a source position to everything so later errors can point at
the exact line and column.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .errors import PebbleSyntaxError

# Single-character instructions that need no operand.
OPERATORS = set("+-*/%=<>!:$\\@^.,?&")

# Escape sequences recognised inside "strings" and 'c char literals.
ESCAPES = {"n": "\n", "t": "\t", "0": "\0", "\\": "\\", '"': '"', "'": "'"}


class Kind(Enum):
    NUMBER = auto()   # 42
    STRING = auto()   # "hi\n"
    CHAR = auto()     # 'x
    OP = auto()       # + - * ...
    LOAD = auto()     # a   (push register a)
    STORE = auto()    # ~a  (pop into register a)
    CALL = auto()     # F   (call word F)
    LBRACKET = auto()  # [  while
    RBRACKET = auto()  # ]
    LBRACE = auto()   # {  if
    RBRACE = auto()   # }
    LPAREN = auto()   # (F  begin definition of word F
    RPAREN = auto()   # )
    EOF = auto()


@dataclass(frozen=True)
class Token:
    kind: Kind
    value: object
    line: int
    col: int

    def __repr__(self) -> str:  # compact form used by `pebble --tokens`
        return f"{self.kind.name}({self.value!r})@{self.line}:{self.col}"


SIMPLE = {
    "[": Kind.LBRACKET,
    "]": Kind.RBRACKET,
    "{": Kind.LBRACE,
    "}": Kind.RBRACE,
    ")": Kind.RPAREN,
}


class Lexer:
    """A hand-written, single-pass scanner with one character of lookahead."""

    def __init__(self, source: str) -> None:
        self.src = source
        self.i = 0
        self.line = 1
        self.col = 1

    # -- low-level cursor helpers -------------------------------------
    def _peek(self) -> str:
        return self.src[self.i] if self.i < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _error(self, msg: str, line: int, col: int) -> PebbleSyntaxError:
        return PebbleSyntaxError(msg, line, col)

    def _escape(self, line: int, col: int) -> str:
        """Read the character after a backslash and translate it."""
        if not self._peek():
            raise self._error("unfinished escape sequence", line, col)
        ch = self._advance()
        if ch not in ESCAPES:
            raise self._error(f"unknown escape '\\{ch}'", line, col)
        return ESCAPES[ch]

    # -- main loop ----------------------------------------------------
    def tokens(self) -> list[Token]:
        out: list[Token] = []
        while self.i < len(self.src):
            ch = self._peek()
            line, col = self.line, self.col

            if ch.isspace():
                self._advance()
            elif ch == "#":  # comment runs to end of line
                while self._peek() and self._peek() != "\n":
                    self._advance()
            elif ch.isdigit():
                digits = ""
                while self._peek().isdigit():
                    digits += self._advance()
                out.append(Token(Kind.NUMBER, int(digits), line, col))
            elif ch == '"':
                self._advance()
                chars = []
                while True:
                    c = self._peek()
                    if not c:
                        raise self._error("unterminated string", line, col)
                    self._advance()
                    if c == '"':
                        break
                    chars.append(self._escape(line, col) if c == "\\" else c)
                out.append(Token(Kind.STRING, "".join(chars), line, col))
            elif ch == "'":
                self._advance()
                c = self._peek()
                if not c:
                    raise self._error("expected a character after '", line, col)
                self._advance()
                if c == "\\":
                    c = self._escape(line, col)
                out.append(Token(Kind.CHAR, ord(c), line, col))
            elif ch == "~":
                self._advance()
                name = self._peek()
                if not ("a" <= name <= "z"):
                    raise self._error("'~' must be followed by a register a-z", line, col)
                self._advance()
                out.append(Token(Kind.STORE, name, line, col))
            elif ch == "(":
                self._advance()
                name = self._peek()
                if not ("A" <= name <= "Z"):
                    raise self._error("'(' must be followed by a word name A-Z", line, col)
                self._advance()
                out.append(Token(Kind.LPAREN, name, line, col))
            elif "a" <= ch <= "z":
                out.append(Token(Kind.LOAD, self._advance(), line, col))
            elif "A" <= ch <= "Z":
                out.append(Token(Kind.CALL, self._advance(), line, col))
            elif ch in SIMPLE:
                out.append(Token(SIMPLE[ch], self._advance(), line, col))
            elif ch in OPERATORS:
                out.append(Token(Kind.OP, self._advance(), line, col))
            else:
                raise self._error(f"unexpected character {ch!r}", line, col)

        out.append(Token(Kind.EOF, None, self.line, self.col))
        return out


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokens()
