from datetime import date

import pytest

from todo_cli.dates import describe_due, parse_due

TODAY = date(2026, 10, 22)  # a Thursday


@pytest.mark.parametrize("text,expected", [
    ("today", TODAY),
    ("tomorrow", date(2026, 10, 23)),
    ("+3d", date(2026, 10, 25)),
    ("+2w", date(2026, 11, 5)),
    ("2027-01-15", date(2027, 1, 15)),
    ("fri", date(2026, 10, 23)),
    ("Monday", date(2026, 10, 26)),
    ("thu", date(2026, 10, 29)),  # same weekday means next week, not today
    ("none", None),
])
def test_parse_due(text, expected):
    assert parse_due(text, TODAY) == expected


@pytest.mark.parametrize("bad", ["next tuesday", "2026-13-01", "+3x", "fr"])
def test_parse_due_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_due(bad, TODAY)


@pytest.mark.parametrize("due,text", [
    (TODAY, "today"),
    (date(2026, 10, 23), "tomorrow"),
    (date(2026, 10, 21), "yesterday"),
    (date(2026, 10, 30), "in 8d"),
    (date(2026, 10, 19), "3d overdue"),
])
def test_describe_due(due, text):
    assert describe_due(due, TODAY) == text
