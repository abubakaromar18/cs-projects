"""Core data model: the Task record and the Priority enum.

Tasks are plain dataclasses so they serialise cleanly to/from JSON. All
conversion logic lives here so the storage layer stays format-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import IntEnum
from typing import Any


class Priority(IntEnum):
    """Task priority. IntEnum lets us sort by priority numerically."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def parse(cls, text: str) -> "Priority":
        """Accept 'high', 'H', 'med', '3', etc. (case-insensitive)."""
        key = text.strip().lower()
        aliases = {
            "l": cls.LOW, "low": cls.LOW, "1": cls.LOW,
            "m": cls.MEDIUM, "med": cls.MEDIUM, "medium": cls.MEDIUM, "2": cls.MEDIUM,
            "h": cls.HIGH, "hi": cls.HIGH, "high": cls.HIGH, "3": cls.HIGH,
        }
        try:
            return aliases[key]
        except KeyError:
            raise ValueError(f"unknown priority {text!r} (use low, medium or high)") from None

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass
class Task:
    """A single to-do item."""

    id: int
    title: str
    priority: Priority = Priority.MEDIUM
    due: date | None = None
    done: bool = False
    created: datetime = field(default_factory=lambda: datetime.now().replace(microsecond=0))
    completed: datetime | None = None
    tags: list[str] = field(default_factory=list)

    # ---- behaviour -----------------------------------------------------

    def mark_done(self, when: datetime | None = None) -> None:
        self.done = True
        self.completed = (when or datetime.now()).replace(microsecond=0)

    def mark_undone(self) -> None:
        self.done = False
        self.completed = None

    def is_overdue(self, today: date | None = None) -> bool:
        """A task is overdue if it is still open and its due date has passed."""
        if self.done or self.due is None:
            return False
        return self.due < (today or date.today())

    # ---- (de)serialisation --------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority.label,
            "due": self.due.isoformat() if self.due else None,
            "done": self.done,
            "created": self.created.isoformat(),
            "completed": self.completed.isoformat() if self.completed else None,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Build a Task from a JSON dict, validating required fields."""
        try:
            return cls(
                id=int(data["id"]),
                title=str(data["title"]),
                priority=Priority.parse(str(data.get("priority", "medium"))),
                due=date.fromisoformat(data["due"]) if data.get("due") else None,
                done=bool(data.get("done", False)),
                created=datetime.fromisoformat(data["created"]) if data.get("created") else datetime.now().replace(microsecond=0),
                completed=datetime.fromisoformat(data["completed"]) if data.get("completed") else None,
                tags=[str(t) for t in data.get("tags", [])],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid task record: {data!r} ({exc})") from exc


def sort_key(mode: str, today: date | None = None):
    """Return a key function for sorting tasks.

    Modes:
      * ``smart``    – open before done, overdue first, then priority (high→low),
                       then nearest due date, then id. This is the default view.
      * ``priority`` – high→low, ties by id.
      * ``due``      – earliest due first; tasks with no due date go last.
      * ``created``  – oldest first (equivalent to id order).
    """
    today = today or date.today()
    far_future = date.max

    if mode == "smart":
        return lambda t: (t.done, not t.is_overdue(today), -t.priority, t.due or far_future, t.id)
    if mode == "priority":
        return lambda t: (-t.priority, t.id)
    if mode == "due":
        return lambda t: (t.due is None, t.due or far_future, t.id)
    if mode == "created":
        return lambda t: (t.created, t.id)
    raise ValueError(f"unknown sort mode {mode!r}")
