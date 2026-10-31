"""Storage layer (the Repository pattern).

The HTTP layer only talks to the abstract ``TodoRepository``. Two implementations
are provided and the test suite runs every API test against both:

* ``InMemoryTodoRepository``  a dict guarded by a lock; fast, used by default
* ``SqliteTodoRepository``    stdlib ``sqlite3`` with parameterised SQL; survives restarts

Swapping storage therefore never touches the routes, which is the point of the pattern.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable

from .schemas import Priority, SortField, Stats, Todo, TodoCreate

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TodoQuery:
    """Filtering, sorting and pagination options for listing todos."""

    completed: bool | None = None
    priority: Priority | None = None
    tag: str | None = None
    search: str | None = None          # case-insensitive substring of title or notes
    due_before: date | None = None     # inclusive
    sort: SortField = SortField.created_at
    descending: bool = False
    limit: int = 20
    offset: int = 0


class TodoRepository(ABC):
    def __init__(self, clock: Clock = utc_now) -> None:
        self._clock = clock

    @abstractmethod
    def create(self, data: TodoCreate) -> Todo: ...

    @abstractmethod
    def get(self, todo_id: int) -> Todo | None: ...

    @abstractmethod
    def list(self, query: TodoQuery) -> tuple[list[Todo], int]:
        """Return one page of matching todos and the total number of matches."""

    @abstractmethod
    def update(self, todo_id: int, changes: dict[str, Any]) -> Todo | None:
        """Apply a partial update. Returns None if the todo does not exist."""

    @abstractmethod
    def delete(self, todo_id: int) -> bool: ...

    @abstractmethod
    def all(self) -> list[Todo]: ...

    def stats(self, today: date) -> Stats:
        """Aggregate counts. Written once here on top of ``all()``."""
        todos = self.all()
        done = sum(t.completed for t in todos)
        overdue = sum(1 for t in todos if not t.completed and t.due_date and t.due_date < today)
        by_priority = {p: 0 for p in Priority}
        for t in todos:
            by_priority[t.priority] += 1
        return Stats(total=len(todos), completed=done, open=len(todos) - done,
                     overdue=overdue, by_priority=by_priority)


# --------------------------------------------------------------------------- in-memory

def _sort_key(sort: SortField) -> Callable[[Todo], Any]:
    """Key functions for in-memory sorting. ``id`` breaks ties so order is stable.

    Todos without a due date sort after those with one (in ascending order).
    """
    if sort is SortField.due_date:
        return lambda t: (t.due_date is None, t.due_date or date.min, t.id)
    if sort is SortField.priority:
        return lambda t: (t.priority.rank, t.id)
    if sort is SortField.title:
        return lambda t: (t.title.casefold(), t.id)
    return lambda t: (t.created_at, t.id)


class InMemoryTodoRepository(TodoRepository):
    def __init__(self, clock: Clock = utc_now) -> None:
        super().__init__(clock)
        self._items: dict[int, Todo] = {}
        self._next_id = 1
        # FastAPI runs sync endpoints in a thread pool, so mutations need a lock.
        self._lock = threading.Lock()

    def create(self, data: TodoCreate) -> Todo:
        with self._lock:
            now = self._clock()
            todo = Todo(id=self._next_id, created_at=now, updated_at=now, **data.model_dump())
            self._items[todo.id] = todo
            self._next_id += 1
            return todo

    def get(self, todo_id: int) -> Todo | None:
        return self._items.get(todo_id)

    def list(self, query: TodoQuery) -> tuple[list[Todo], int]:
        with self._lock:
            items = list(self._items.values())

        def matches(t: Todo) -> bool:
            if query.completed is not None and t.completed != query.completed:
                return False
            if query.priority is not None and t.priority != query.priority:
                return False
            if query.tag is not None and query.tag.lower() not in t.tags:
                return False
            if query.due_before is not None and (t.due_date is None or t.due_date > query.due_before):
                return False
            if query.search:
                needle = query.search.casefold()
                if needle not in t.title.casefold() and needle not in t.notes.casefold():
                    return False
            return True

        hits = sorted(filter(matches, items), key=_sort_key(query.sort), reverse=query.descending)
        return hits[query.offset: query.offset + query.limit], len(hits)

    def update(self, todo_id: int, changes: dict[str, Any]) -> Todo | None:
        with self._lock:
            current = self._items.get(todo_id)
            if current is None:
                return None
            updated = current.model_copy(update={**changes, "updated_at": self._clock()})
            self._items[todo_id] = updated
            return updated

    def delete(self, todo_id: int) -> bool:
        with self._lock:
            return self._items.pop(todo_id, None) is not None

    def all(self) -> list[Todo]:
        with self._lock:
            return list(self._items.values())


# --------------------------------------------------------------------------- SQLite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    notes       TEXT    NOT NULL DEFAULT '',
    priority    TEXT    NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    due_date    TEXT,                    -- ISO 8601 date or NULL
    tags        TEXT    NOT NULL DEFAULT '[]',  -- JSON array
    completed   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""

# Whitelisted ORDER BY expressions. Column names can't be bound as SQL parameters,
# so user input is mapped through this dict and never interpolated directly.
_ORDER_BY = {
    SortField.created_at: "created_at {dir}, id {dir}",
    SortField.due_date: "due_date IS NULL {nulls}, due_date {dir}, id {dir}",
    SortField.priority: "CASE priority WHEN 'low' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END {dir}, id {dir}",
    SortField.title: "title COLLATE NOCASE {dir}, id {dir}",
}


class SqliteTodoRepository(TodoRepository):
    def __init__(self, path: str = ":memory:", clock: Clock = utc_now) -> None:
        super().__init__(clock)
        # One shared connection; the lock serialises access across worker threads.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    @staticmethod
    def _row_to_todo(row: sqlite3.Row) -> Todo:
        return Todo(
            id=row["id"],
            title=row["title"],
            notes=row["notes"],
            priority=Priority(row["priority"]),
            due_date=date.fromisoformat(row["due_date"]) if row["due_date"] else None,
            tags=json.loads(row["tags"]),
            completed=bool(row["completed"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create(self, data: TodoCreate) -> Todo:
        now = self._clock().isoformat()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO todos (title, notes, priority, due_date, tags, completed,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (data.title, data.notes, data.priority.value,
                 data.due_date.isoformat() if data.due_date else None,
                 json.dumps(data.tags), int(data.completed), now, now),
            )
            new_id = cur.lastrowid
        return self.get(new_id)  # type: ignore[return-value]

    def get(self, todo_id: int) -> Todo | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        return self._row_to_todo(row) if row else None

    def list(self, query: TodoQuery) -> tuple[list[Todo], int]:
        where, params = [], []
        if query.completed is not None:
            where.append("completed = ?")
            params.append(int(query.completed))
        if query.priority is not None:
            where.append("priority = ?")
            params.append(query.priority.value)
        if query.tag is not None:
            # json_each expands the tags array into rows we can match against.
            where.append("EXISTS (SELECT 1 FROM json_each(todos.tags) WHERE value = ?)")
            params.append(query.tag.lower())
        if query.due_before is not None:
            where.append("due_date IS NOT NULL AND due_date <= ?")
            params.append(query.due_before.isoformat())
        if query.search:
            # instr(lower(..)) avoids LIKE wildcards in user input needing escaping.
            where.append("(instr(lower(title), ?) > 0 OR instr(lower(notes), ?) > 0)")
            params += [query.search.lower()] * 2

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        direction = "DESC" if query.descending else "ASC"
        # NULL due dates go last when ascending, first when descending (mirrors in-memory).
        order = _ORDER_BY[query.sort].format(dir=direction, nulls=direction)

        with self._lock:
            total = self._conn.execute(f"SELECT COUNT(*) FROM todos {clause}", params).fetchone()[0]
            rows = self._conn.execute(
                f"SELECT * FROM todos {clause} ORDER BY {order} LIMIT ? OFFSET ?",
                [*params, query.limit, query.offset],
            ).fetchall()
        return [self._row_to_todo(r) for r in rows], total

    def update(self, todo_id: int, changes: dict[str, Any]) -> Todo | None:
        encoders = {
            "priority": lambda v: Priority(v).value,
            "due_date": lambda v: v.isoformat() if v else None,
            "tags": json.dumps,
            "completed": int,
        }
        cols = {k: encoders.get(k, lambda v: v)(v) for k, v in changes.items()}
        cols["updated_at"] = self._clock().isoformat()
        # Keys come from the validated TodoUpdate model, never from raw input.
        assignments = ", ".join(f"{k} = ?" for k in cols)
        with self._lock, self._conn:
            cur = self._conn.execute(
                f"UPDATE todos SET {assignments} WHERE id = ?", [*cols.values(), todo_id]
            )
            if cur.rowcount == 0:
                return None
        return self.get(todo_id)

    def delete(self, todo_id: int) -> bool:
        with self._lock, self._conn:
            return self._conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,)).rowcount > 0

    def all(self) -> list[Todo]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM todos").fetchall()
        return [self._row_to_todo(r) for r in rows]
