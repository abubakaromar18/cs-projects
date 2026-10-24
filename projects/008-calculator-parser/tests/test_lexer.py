import pytest

from calc.errors import LexError
from calc.lexer import TokenType as T
from calc.lexer import tokenize


def types(src):
    return [t.type for t in tokenize(src)]


def test_simple_expression():
    assert types("1 + 2*3") == [T.NUMBER, T.PLUS, T.NUMBER, T.STAR, T.NUMBER, T.EOF]


@pytest.mark.parametrize(
    "src, value",
    [("42", 42), ("3.25", 3.25), (".5", 0.5), ("1e3", 1000), ("2.5E-2", 0.025), ("7.", 7)],
)
def test_number_formats(src, value):
    tok = tokenize(src)[0]
    assert tok.type is T.NUMBER and tok.value == pytest.approx(value)


def test_exponent_without_digits_is_not_consumed():
    # "2e" is the number 2 followed by the identifier e (Euler's number).
    toks = tokenize("2e")
    assert [t.type for t in toks] == [T.NUMBER, T.IDENT, T.EOF]


def test_two_char_operators():
    assert types("2**3 // 4") == [T.NUMBER, T.CARET, T.NUMBER, T.DSLASH, T.NUMBER, T.EOF]


def test_identifiers_and_positions():
    toks = tokenize("  foo_1 = max(a, b)")
    assert toks[0].text == "foo_1" and toks[0].pos == 2
    assert [t.type for t in toks[2:]] == [
        T.IDENT, T.LPAREN, T.IDENT, T.COMMA, T.IDENT, T.RPAREN, T.EOF,
    ]


def test_bad_character_reports_position():
    with pytest.raises(LexError) as exc:
        tokenize("1 + $")
    assert exc.value.pos == 4
