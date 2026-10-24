import math

import pytest

from calc.errors import EvalError
from calc.evaluator import Evaluator, evaluate, format_number


@pytest.mark.parametrize(
    "src, expected",
    [
        ("1 + 2 * 3", 7),
        ("(1 + 2) * 3", 9),
        ("10 - 4 - 3", 3),
        ("2 ^ 3 ^ 2", 512),
        ("-2 ^ 2", -4),
        ("(-2) ^ 2", 4),
        ("2 ^ -1", 0.5),
        ("7 // 2", 3),
        ("-7 // 2", -4),
        ("7 % 3", 1),
        ("5!", 120),
        ("0!", 1),
        ("3! ^ 2", 36),
        ("sqrt(16) + abs(-3)", 7),
        ("max(1, 9, 4) - min(5, 2)", 7),
        ("log(1000)", 3),
        ("log(8, 2)", 3),
        ("ln(e)", 1),
        ("round(3.14159, 2)", 3.14),
        ("floor(2.7) + ceil(2.1)", 5),
        ("cos(pi)", -1),
        ("1e3 / 4", 250),
    ],
)
def test_values(src, expected):
    assert evaluate(src) == pytest.approx(expected)


def test_matches_python_on_random_expressions():
    """Property-style check: our precedence rules agree with Python's."""
    import random

    rng = random.Random(1234)
    ops = ["+", "-", "*"]
    for _ in range(300):
        parts = [str(rng.randint(0, 9))]
        for _ in range(rng.randint(1, 6)):
            parts += [rng.choice(ops), str(rng.randint(0, 9))]
        src = " ".join(parts)
        assert evaluate(src) == eval(src), src  # noqa: S307 - digits and + - * only


def test_variables_persist_between_lines():
    ev = Evaluator()
    assert ev.evaluate("x = 4") == 4
    assert ev.evaluate("y = x ^ 2") == 16
    assert ev.evaluate("x + y") == 20
    assert ev.evaluate("ans * 2") == 40


def test_chained_assignment():
    ev = Evaluator()
    ev.evaluate("a = b = 3")
    assert ev.variables["a"] == ev.variables["b"] == 3


@pytest.mark.parametrize(
    "src, fragment",
    [
        ("1 / 0", "division by zero"),
        ("5 % 0", "division by zero"),
        ("nope + 1", "undefined variable"),
        ("foo(1)", "unknown function"),
        ("sqrt(1, 2)", "takes 1"),
        ("sqrt(-1)", "sqrt()"),
        ("(-8) ^ 0.5", "not a real number"),
        ("2.5!", "non-negative integer"),
        ("(-1)!", "non-negative integer"),
        ("171!", "too large"),
        ("10 ^ 1000", "too large"),
        ("pi = 3", "cannot assign"),
        ("sqrt + 1", "is a function"),
    ],
)
def test_runtime_errors(src, fragment):
    with pytest.raises(EvalError) as exc:
        evaluate(src)
    assert fragment in exc.value.message


def test_runtime_error_position():
    with pytest.raises(EvalError) as exc:
        evaluate("1 + 2 / 0")
    assert exc.value.pos == 6


@pytest.mark.parametrize(
    "value, text",
    [(3.0, "3"), (-0.5, "-0.5"), (0.1 + 0.2, "0.3"), (math.inf, "inf"), (1e20, "1e+20")],
)
def test_format_number(value, text):
    assert format_number(value) == text


def test_long_flat_chain_within_recursion_limit():
    assert evaluate("+".join(["1"] * 300)) == 300


def test_very_long_chain_fails_cleanly():
    with pytest.raises(EvalError, match="too long"):
        evaluate("+".join(["1"] * 20000))
