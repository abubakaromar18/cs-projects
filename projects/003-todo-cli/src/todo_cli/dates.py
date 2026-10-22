"""Friendly due-date parsing.

Accepts ISO dates plus a few human shortcuts so adding tasks is quick:

    2026-11-05   today   tomorrow   +3d   +2w   mon .. sun   none
"""

from __future__ import annotations

import re
from datetime import date, timedelta

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
# Both "fri" and "friday" map to 4 (Monday == 0, matching date.weekday()).
_WEEKDAY_LOOKUP = {name: i for i, name in enumerate(_WEEKDAYS)} | {
    name[:3]: i for i, name in enumerate(_WEEKDAYS)
}
_RELATIVE = re.compile(r"^\+(\d+)([dw])$")


def parse_due(text: str, today: date | None = None) -> date | None:
    """Parse a due-date expression relative to ``today``.

    Returns ``None`` for "none"/"" (used to clear a due date).
    Raises ``ValueError`` for anything unrecognised.
    """
    today = today or date.today()
    s = text.strip().lower()

    if s in ("", "none", "-"):
        return None
    if s in ("today", "tod"):
        return today
    if s in ("tomorrow", "tom", "tmr"):
        return today + timedelta(days=1)

    m = _RELATIVE.match(s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return today + timedelta(days=n * (7 if unit == "w" else 1))

    # Weekday names: the *next* occurrence, never today (so "fri" on a Friday
    # means a week from now — matching how people usually say it).
    if s in _WEEKDAY_LOOKUP:
        target = _WEEKDAY_LOOKUP[s]
        delta = (target - today.weekday()) % 7 or 7
        return today + timedelta(days=delta)

    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ValueError(
            f"can't understand due date {text!r} "
            "(try YYYY-MM-DD, today, tomorrow, +3d, +2w, or a weekday)"
        ) from None


def describe_due(due: date, today: date | None = None) -> str:
    """Human-friendly relative description, e.g. 'today', 'in 3d', '2d overdue'."""
    today = today or date.today()
    diff = (due - today).days
    if diff == 0:
        return "today"
    if diff == 1:
        return "tomorrow"
    if diff == -1:
        return "yesterday"
    if diff < 0:
        return f"{-diff}d overdue"
    return f"in {diff}d"
