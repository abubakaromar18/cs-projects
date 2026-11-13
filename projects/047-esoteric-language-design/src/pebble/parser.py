"""Recursive-descent parser: tokens -> AST.

Grammar (EBNF):

    program    = { item } EOF ;
    item       = definition | statement ;
    definition = "(" WORD { statement } ")" ;          (top level only)
    statement  = NUMBER | STRING | CHAR | OP | LOAD | STORE | CALL
               | "[" { statement } "]"
               | "{" { statement } "}" ;

Because the grammar is LL(1) — the next token alone decides which rule
applies — each rule is just one small method.
"""

from __future__ import annotations

from collections.abc import Iterable

from . import ast
from .errors import PebbleSyntaxError
from .lexer import Kind, Token, tokenize

CLOSERS = {Kind.LBRACKET: Kind.RBRACKET, Kind.LBRACE: Kind.RBRACE, Kind.LPAREN: Kind.RPAREN}
CLOSER_TEXT = {Kind.RBRACKET: "]", Kind.RBRACE: "}", Kind.RPAREN: ")"}


class Parser:
    def __init__(self, tokens: list[Token], known_words: Iterable[str] = ()) -> None:
        self.toks = tokens
        self.pos = 0
        # Words defined by earlier runs (e.g. previous REPL lines) count as defined.
        self.known = set(known_words)

    def _peek(self) -> Token:
        return self.toks[self.pos]

    def _next(self) -> Token:
        tok = self.toks[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> ast.Program:
        body: list[ast.Node] = []
        words: dict[str, ast.Define] = {}
        while self._peek().kind is not Kind.EOF:
            if self._peek().kind is Kind.LPAREN:
                d = self._definition()
                if d.word in words:
                    raise PebbleSyntaxError(f"word {d.word} is defined twice", d.line, d.col)
                words[d.word] = d
            else:
                body.append(self._statement())
        # Every call must name a defined word; catching this now gives a
        # better error than failing halfway through a run.
        for node in _walk(body + list(words.values())):
            if isinstance(node, ast.Call) and node.word not in words and node.word not in self.known:
                raise PebbleSyntaxError(f"call to undefined word {node.word}", node.line, node.col)
        return ast.Program(body, words)

    def _definition(self) -> ast.Define:
        open_tok = self._next()
        return ast.Define(open_tok.line, open_tok.col, open_tok.value, self._block(open_tok))

    def _block(self, open_tok: Token) -> list[ast.Node]:
        """Parse statements until the matching closer of `open_tok`."""
        closer = CLOSERS[open_tok.kind]
        body: list[ast.Node] = []
        while True:
            tok = self._peek()
            if tok.kind is closer:
                self._next()
                return body
            if tok.kind is Kind.EOF:
                raise PebbleSyntaxError(
                    f"'{open_tok.value if open_tok.kind is not Kind.LPAREN else '('}' "
                    f"is never closed (expected '{CLOSER_TEXT[closer]}')",
                    open_tok.line,
                    open_tok.col,
                )
            if tok.kind is Kind.LPAREN:
                raise PebbleSyntaxError("definitions are only allowed at top level", tok.line, tok.col)
            body.append(self._statement())

    def _statement(self) -> ast.Node:
        tok = self._next()
        k, v, line, col = tok.kind, tok.value, tok.line, tok.col
        if k in (Kind.NUMBER, Kind.CHAR):
            return ast.Push(line, col, v)
        if k is Kind.STRING:
            return ast.PushString(line, col, v)
        if k is Kind.OP:
            return ast.Op(line, col, v)
        if k is Kind.LOAD:
            return ast.Load(line, col, v)
        if k is Kind.STORE:
            return ast.Store(line, col, v)
        if k is Kind.CALL:
            return ast.Call(line, col, v)
        if k is Kind.LBRACKET:
            return ast.While(line, col, self._block(tok))
        if k is Kind.LBRACE:
            return ast.If(line, col, self._block(tok))
        # Only stray closers can reach here.
        raise PebbleSyntaxError(f"unexpected '{v}' with nothing to close", line, col)


def _walk(nodes):
    for n in nodes:
        yield n
        if isinstance(n, (ast.While, ast.If, ast.Define)):
            yield from _walk(n.body)


def parse(source: str, known_words: Iterable[str] = ()) -> ast.Program:
    return Parser(tokenize(source), known_words).parse()
