import pytest

from intentbot import calc
from intentbot.rules import Rule, RuleEngine


def test_rule_extracts_named_groups():
    r = Rule("set_name", r"my name is (?P<name>\w+)")
    m = r.match("Hi, MY NAME IS Ada")
    assert m.intent == "set_name" and m.slots == {"name": "Ada"}


def test_priority_beats_definition_order():
    eng = RuleEngine([Rule("low", r"hello"), Rule("high", r"hello", priority=5)])
    assert eng.match("hello").intent == "high"


def test_ties_keep_definition_order():
    eng = RuleEngine([Rule("first", r"x"), Rule("second", r"x")])
    assert eng.match("x").intent == "first"


def test_no_match_returns_none():
    assert RuleEngine([Rule("a", r"zzz")]).match("hello") is None


@pytest.mark.parametrize(
    "expr,value",
    [("2 + 2", 4), ("3 * (4 + 2)", 18), ("2^10", 1024), ("-5 + 3", -2), ("7 // 2", 3), ("10 % 4", 2), ("6 x 7", 42)],
)
def test_calc_evaluates(expr, value):
    assert calc.evaluate(expr) == value


@pytest.mark.parametrize("expr", ["__import__('os')", "a + 1", "1/0", "9**9**9", "2 +", "True + 1"])
def test_calc_rejects_unsafe_or_invalid(expr):
    with pytest.raises(calc.CalcError):
        calc.evaluate(expr)
