"""Lexer: turns a source string into a flat list of tokens.

The lexer is a hand-written scanner that walks the string one character at a
time. It knows nothing about precedence or structure; that is the parser's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .errors import LexError


class TokenType(Enum):
    NUMBER = auto()
    IDENT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    DSLASH = auto()   # //  floor division
    PERCENT = auto()
    CARET = auto()    # ^ or **  exponentiation
    BANG = auto()     # !  factorial
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EQUALS = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    text: str
    pos: int                 # offset of the first character in the source
    value: float | None = None  # numeric value for NUMBER tokens


# Single-character operators. Multi-character ones (**, //) are handled first.
_SIMPLE = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "^": TokenType.CARET,
    "!": TokenType.BANG,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
    "=": TokenType.EQUALS,
}


def tokenize(source: str) -> list[Token]:
    """Scan `source` and return its tokens, always ending with an EOF token."""
    tokens: list[Token] = []
    i, n = 0, len(source)

    while i < n:
        ch = source[i]

        if ch.isspace():
            i += 1
            continue

        # Numbers: 12, 3.5, .5, 1e10, 2.5E-3
        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            start = i
            while i < n and source[i].isdigit():
                i += 1
            if i < n and source[i] == ".":
                i += 1
                while i < n and source[i].isdigit():
                    i += 1
            # Optional exponent, only consumed if digits actually follow.
            if i < n and source[i] in "eE":
                j = i + 1
                if j < n and source[j] in "+-":
                    j += 1
                if j < n and source[j].isdigit():
                    i = j
                    while i < n and source[i].isdigit():
                        i += 1
            text = source[start:i]
            tokens.append(Token(TokenType.NUMBER, text, start, float(text)))
            continue

        # Identifiers: variable and function names.
        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            tokens.append(Token(TokenType.IDENT, source[start:i], start))
            continue

        # Two-character operators must be checked before their one-char prefixes.
        two = source[i : i + 2]
        if two == "**":
            tokens.append(Token(TokenType.CARET, two, i))
            i += 2
            continue
        if two == "//":
            tokens.append(Token(TokenType.DSLASH, two, i))
            i += 2
            continue

        if ch in _SIMPLE:
            tokens.append(Token(_SIMPLE[ch], ch, i))
            i += 1
            continue

        raise LexError(f"unexpected character {ch!r}", i)

    tokens.append(Token(TokenType.EOF, "", n))
    return tokens
