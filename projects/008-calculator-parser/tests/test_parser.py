"""The parser is tested through S-expressions, which make tree shape explicit."""

import pytest

from calc.ast import to_sexpr
from calc.errors import ParseError
from calc.parser import MAX_DEPTH, parse


def sx(src):
    return to_sexpr(parse(src))


@pytest.mark.parametrize(
    "src, tree",
    [
        # precedence
        ("1 + 2 * 3", "(+ 1 (* 2 3))"),
        ("(1 + 2) * 3", "(* (+ 1 2) 3)"),
        ("2 * 3 ^ 2", "(* 2 (^ 3 2))"),
        ("10 - 6 % 4", "(- 10 (% 6 4))"),
        # left associativity
        ("1 - 2 - 3", "(- (- 1 2) 3)"),
        ("8 / 4 / 2", "(/ (/ 8 4) 2)"),
        ("7 // 2 * 3", "(* (// 7 2) 3)"),
        # right associativity of ^
        ("2 ^ 3 ^ 2", "(^ 2 (^ 3 2))"),
        ("2 ** 3 ** 2", "(^ 2 (^ 3 2))"),
        # unary minus binds looser than ^, tighter than *
        ("-2 ^ 2", "(neg (^ 2 2))"),
        ("2 ^ -1", "(^ 2 (neg 1))"),
        ("-3 * 2", "(* (neg 3) 2)"),
        ("--4", "(neg (neg 4))"),
        ("+4", "(pos 4)"),
        # postfix factorial binds tightest
        ("3! ^ 2", "(^ (! 3) 2)"),
        ("-3!", "(neg (! 3))"),
        ("3!!", "(! (! 3))"),
        # calls, names, assignment
        ("max(1, 2 + 3, x)", "(max 1 (+ 2 3) x)"),
        ("f()", "(f)"),
        ("x = y = 2 + 1", "(= x (= y (+ 2 1)))"),
        ("(x = 2) * 3", "(* (= x 2) 3)"),
    ],
)
def test_tree_shape(src, tree):
    assert sx(src) == tree


@pytest.mark.parametrize(
    "src, pos",
    [
        ("", 0),
        ("1 +", 3),
        ("(1 + 2", 6),
        ("1 2", 2),
        ("* 3", 0),
        ("max(1, )", 7),
        ("max(1 2)", 6),
        ("1 = 2", 2),
    ],
)
def test_syntax_errors_point_at_the_problem(src, pos):
    with pytest.raises(ParseError) as exc:
        parse(src)
    assert exc.value.pos == pos


def test_error_render_has_caret():
    with pytest.raises(ParseError) as exc:
        parse("1 + * 2")
    rendered = exc.value.render("1 + * 2")
    assert rendered.splitlines()[1] == "    ^"
    assert "Parse error" in rendered


def test_nesting_within_limit():
    src = "(" * MAX_DEPTH + "1" + ")" * MAX_DEPTH
    assert sx(src) == "1"


@pytest.mark.parametrize("src", ["(" * 5000 + "1" + ")" * 5000, "-" * 5000 + "1", "^".join(["2"] * 5000)])
def test_excessive_nesting_is_a_parse_error_not_a_crash(src):
    with pytest.raises(ParseError, match="nested too deeply"):
        parse(src)
