"""Recursive descent parser.

Each grammar rule below becomes one method. Precedence comes from the call
chain: a rule only calls rules that bind *tighter* than itself, so lower rules
in the list end up deeper in the tree and get evaluated first.

    statement      := assignment EOF
    assignment     := IDENT "=" assignment          (right-associative)
                    | additive
    additive       := multiplicative (("+" | "-") multiplicative)*
    multiplicative := unary (("*" | "/" | "//" | "%") unary)*
    unary          := ("+" | "-") unary
                    | power
    power          := postfix ("^" unary)?           (right-associative)
    postfix        := primary "!"*
    primary        := NUMBER
                    | IDENT "(" arguments? ")"
                    | IDENT
                    | "(" assignment ")"
    arguments      := assignment ("," assignment)*

Two classic subtleties this grammar gets right:

* `-2^2` is -4, not 4: unary minus sits *above* power, so the power is
  parsed first and then negated (the same rule as in maths and Python).
* `2^-1` works: the right operand of `^` is a `unary`, so it may carry a sign.
  And because that `unary` can recurse into `power`, `2^3^2` is 2^(3^2) = 512.

Left-associative operators use a loop (iteration) instead of left recursion,
which a recursive descent parser can't handle directly.
"""

from __future__ import annotations

from .ast import Assign, BinaryOp, Call, Factorial, Name, Node, Number, UnaryOp
from .errors import ParseError
from .lexer import Token, TokenType, tokenize

_ADDITIVE = {TokenType.PLUS: "+", TokenType.MINUS: "-"}
_MULTIPLICATIVE = {
    TokenType.STAR: "*",
    TokenType.SLASH: "/",
    TokenType.DSLASH: "//",
    TokenType.PERCENT: "%",
}


# Each nesting level ("(", a call, a prefix sign) costs several Python stack
# frames, so we cap it and fail with a clean ParseError instead of crashing
# with RecursionError on hostile input like "((((((...".
MAX_DEPTH = 100


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.i = 0
        self.depth = 0

    def _enter(self, pos: int) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ParseError(f"expression nested too deeply (limit {MAX_DEPTH})", pos)

    # ---- token helpers -------------------------------------------------

    @property
    def current(self) -> Token:
        return self.tokens[self.i]

    def peek(self, offset: int = 1) -> Token:
        j = min(self.i + offset, len(self.tokens) - 1)
        return self.tokens[j]

    def advance(self) -> Token:
        tok = self.current
        if tok.type is not TokenType.EOF:
            self.i += 1
        return tok

    def expect(self, ttype: TokenType, what: str) -> Token:
        if self.current.type is not ttype:
            raise ParseError(f"expected {what}, found {_describe(self.current)}", self.current.pos)
        return self.advance()

    # ---- grammar rules -------------------------------------------------

    def parse(self) -> Node:
        if self.current.type is TokenType.EOF:
            raise ParseError("empty expression", self.current.pos)
        node = self.assignment()
        if self.current.type is not TokenType.EOF:
            raise ParseError(f"unexpected {_describe(self.current)}", self.current.pos)
        return node

    def assignment(self) -> Node:
        # One token of lookahead decides between `x = ...` and an expression.
        if self.current.type is TokenType.IDENT and self.peek().type is TokenType.EQUALS:
            name = self.advance()
            self.advance()  # '='
            return Assign(name.text, self.assignment(), name.pos)
        return self.additive()

    def additive(self) -> Node:
        node = self.multiplicative()
        while self.current.type in _ADDITIVE:
            op = self.advance()
            node = BinaryOp(_ADDITIVE[op.type], node, self.multiplicative(), op.pos)
        return node

    def multiplicative(self) -> Node:
        node = self.unary()
        while self.current.type in _MULTIPLICATIVE:
            op = self.advance()
            node = BinaryOp(_MULTIPLICATIVE[op.type], node, self.unary(), op.pos)
        return node

    def unary(self) -> Node:
        if self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            self._enter(op.pos)
            node = UnaryOp(op.text, self.unary(), op.pos)
            self.depth -= 1
            return node
        return self.power()

    def power(self) -> Node:
        base = self.postfix()
        if self.current.type is TokenType.CARET:
            op = self.advance()
            # Recursing into unary (not a loop) makes ^ right-associative.
            self._enter(op.pos)
            node = BinaryOp("^", base, self.unary(), op.pos)
            self.depth -= 1
            return node
        return base

    def postfix(self) -> Node:
        node = self.primary()
        while self.current.type is TokenType.BANG:
            node = Factorial(node, self.advance().pos)
        return node

    def primary(self) -> Node:
        tok = self.current

        if tok.type is TokenType.NUMBER:
            self.advance()
            assert tok.value is not None
            return Number(tok.value, tok.pos)

        if tok.type is TokenType.IDENT:
            self.advance()
            if self.current.type is TokenType.LPAREN:
                return self.call(tok)
            return Name(tok.text, tok.pos)

        if tok.type is TokenType.LPAREN:
            self.advance()
            self._enter(tok.pos)
            node = self.assignment()
            self.expect(TokenType.RPAREN, "')'")
            self.depth -= 1
            return node

        raise ParseError(f"expected a number, name or '(', found {_describe(tok)}", tok.pos)

    def call(self, name: Token) -> Node:
        self.advance()  # '('
        self._enter(name.pos)
        args: list[Node] = []
        if self.current.type is not TokenType.RPAREN:
            args.append(self.assignment())
            while self.current.type is TokenType.COMMA:
                self.advance()
                args.append(self.assignment())
        self.expect(TokenType.RPAREN, "',' or ')'")
        self.depth -= 1
        return Call(name.text, tuple(args), name.pos)


def _describe(tok: Token) -> str:
    return "end of input" if tok.type is TokenType.EOF else repr(tok.text)


def parse(source: str) -> Node:
    """Tokenize and parse `source` into an AST."""
    return Parser(tokenize(source)).parse()
