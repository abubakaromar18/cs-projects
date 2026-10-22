from datetime import date, datetime

import pytest

from todo_cli.models import Priority, Task, sort_key

TODAY = date(2026, 10, 22)


@pytest.mark.parametrize("text,expected", [
    ("high", Priority.HIGH), ("H", Priority.HIGH), ("3", Priority.HIGH),
    ("med", Priority.MEDIUM), ("Medium", Priority.MEDIUM),
    ("low", Priority.LOW), (" l ", Priority.LOW),
])
def test_priority_parse(text, expected):
    assert Priority.parse(text) is expected


def test_priority_parse_rejects_unknown():
    with pytest.raises(ValueError):
        Priority.parse("urgent")


def test_round_trip_through_dict():
    t = Task(id=7, title="Ship it", priority=Priority.HIGH, due=date(2026, 11, 1),
             tags=["work"], created=datetime(2026, 10, 1, 9, 0))
    t.mark_done(datetime(2026, 10, 2, 12, 30))
    again = Task.from_dict(t.to_dict())
    assert again == t


def test_from_dict_rejects_missing_title():
    with pytest.raises(ValueError):
        Task.from_dict({"id": 1})


def test_overdue_rules():
    assert Task(1, "a", due=date(2026, 10, 21)).is_overdue(TODAY)
    assert not Task(1, "a", due=TODAY).is_overdue(TODAY)        # due today is not overdue
    assert not Task(1, "a").is_overdue(TODAY)                   # no due date
    done = Task(1, "a", due=date(2020, 1, 1))
    done.mark_done()
    assert not done.is_overdue(TODAY)                           # finished work is never overdue


def test_mark_undone_clears_completion():
    t = Task(1, "a")
    t.mark_done()
    t.mark_undone()
    assert not t.done and t.completed is None


def _tasks():
    return [
        Task(1, "low no-due", Priority.LOW),
        Task(2, "high later", Priority.HIGH, due=date(2026, 12, 1)),
        Task(3, "med overdue", Priority.MEDIUM, due=date(2026, 10, 1)),
        Task(4, "high soon", Priority.HIGH, due=date(2026, 10, 25)),
        Task(5, "done high", Priority.HIGH, done=True),
    ]


def test_smart_sort_orders_overdue_then_priority_then_due_then_done():
    ids = [t.id for t in sorted(_tasks(), key=sort_key("smart", TODAY))]
    assert ids == [3, 4, 2, 1, 5]


def test_due_sort_puts_undated_last():
    ids = [t.id for t in sorted(_tasks(), key=sort_key("due", TODAY))]
    assert ids[:3] == [3, 4, 2] and set(ids[3:]) == {1, 5}


def test_priority_sort_is_stable_by_id():
    ids = [t.id for t in sorted(_tasks(), key=sort_key("priority", TODAY))]
    assert ids == [2, 4, 5, 3, 1]


def test_unknown_sort_mode():
    with pytest.raises(ValueError):
        sort_key("random")
