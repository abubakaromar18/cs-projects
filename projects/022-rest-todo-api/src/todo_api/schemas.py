"""Pydantic models: the API's contract.

Three shapes per resource is the usual FastAPI pattern:

* ``TodoCreate``  what a client may send when creating (all validation lives here)
* ``TodoUpdate``  a partial update for PATCH: every field optional
* ``Todo``        what the server returns, including server-owned fields (id, timestamps)

Keeping input and output models separate means a client can never set ``id`` or
``created_at`` and the OpenAPI docs describe each direction precisely.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Titles are trimmed first, then length-checked, so "   " is rejected as empty.
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Tag = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=30,
                      pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
]


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

    @property
    def rank(self) -> int:
        """Numeric rank used for sorting (high sorts first when descending)."""
        return {"low": 0, "medium": 1, "high": 2}[self.value]


class SortField(str, Enum):
    created_at = "created_at"
    due_date = "due_date"
    priority = "priority"
    title = "title"


def _dedupe_tags(tags: list[str] | None) -> list[str] | None:
    """Remove duplicate tags while keeping the client's order."""
    if tags is None:
        return None
    return list(dict.fromkeys(tags))


class TodoCreate(BaseModel):
    title: Title
    notes: Notes = ""
    priority: Priority = Priority.medium
    due_date: date | None = None
    tags: list[Tag] = Field(default_factory=list, max_length=10)
    completed: bool = False

    @field_validator("tags")
    @classmethod
    def _unique_tags(cls, v: list[str]) -> list[str]:
        return _dedupe_tags(v)

    model_config = ConfigDict(
        extra="forbid",  # unknown fields are a 422, not silently dropped
        json_schema_extra={
            "examples": [
                {"title": "Write report", "priority": "high", "due_date": "2026-11-15",
                 "tags": ["work"]}
            ]
        },
    )


class TodoUpdate(BaseModel):
    """PATCH body. Only fields that are present are changed.

    ``model_dump(exclude_unset=True)`` distinguishes "not sent" from "sent as null",
    which matters for ``due_date``: sending ``null`` clears the date.
    """

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    notes: Notes | None = None
    priority: Priority | None = None
    due_date: date | None = None
    tags: list[Tag] | None = Field(default=None, max_length=10)
    completed: bool | None = None

    @field_validator("tags")
    @classmethod
    def _unique_tags(cls, v: list[str] | None) -> list[str] | None:
        return _dedupe_tags(v)

    @field_validator("title", "priority", "completed", "notes", "tags", mode="before")
    @classmethod
    def _not_null(cls, v, info):
        # Only due_date may be explicitly cleared with null.
        if v is None:
            raise ValueError(f"{info.field_name} may not be null")
        return v


class Todo(BaseModel):
    id: int
    title: str
    notes: str
    priority: Priority
    due_date: date | None
    tags: list[str]
    completed: bool
    created_at: datetime
    updated_at: datetime


class TodoPage(BaseModel):
    """A page of results plus enough metadata for a client to paginate."""

    items: list[Todo]
    total: int
    limit: int
    offset: int


class Stats(BaseModel):
    total: int
    completed: int
    open: int
    overdue: int
    by_priority: dict[Priority, int]
