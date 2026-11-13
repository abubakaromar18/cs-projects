import pytest

from pebble import PebbleSyntaxError, tokenize
from pebble.lexer import Kind


def kinds(src):
    return [t.kind for t in tokenize(src)][:-1]  # drop EOF


def values(src):
    return [t.value for t in tokenize(src)][:-1]


def test_multi_digit_numbers_are_one_token():
    assert values("12 345") == [12, 345]
    assert kinds("12 345") == [Kind.NUMBER, Kind.NUMBER]


def test_adjacent_digits_and_ops():
    assert values("1 2+") == [1, 2, "+"]


def test_string_with_escapes():
    (tok,) = tokenize(r'"a\n\"b\\"')[:-1]
    assert tok.kind is Kind.STRING
    assert tok.value == 'a\n"b\\'


def test_char_literal_and_escaped_char():
    assert values("'A '\\n") == [65, 10]


def test_comments_are_ignored():
    assert values("1 # 2 3 +\n4") == [1, 4]


def test_registers_words_and_definitions():
    toks = tokenize("~a a F (G )")[:-1]
    assert [(t.kind, t.value) for t in toks] == [
        (Kind.STORE, "a"),
        (Kind.LOAD, "a"),
        (Kind.CALL, "F"),
        (Kind.LPAREN, "G"),
        (Kind.RPAREN, ")"),
    ]


def test_positions_track_lines_and_columns():
    toks = tokenize("1\n  +")
    assert (toks[1].line, toks[1].col) == (2, 3)


@pytest.mark.parametrize(
    "src, fragment",
    [
        ('"abc', "unterminated string"),
        ("~1", "register a-z"),
        ("(a", "word name A-Z"),
        ("'", "expected a character"),
        ('"\\q"', "unknown escape"),
        ("1 ` 2", "unexpected character"),
    ],
)
def test_lex_errors(src, fragment):
    with pytest.raises(PebbleSyntaxError, match=fragment):
        tokenize(src)
