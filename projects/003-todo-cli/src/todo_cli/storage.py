"""JSON persistence for the task list.

File format (versioned so it can evolve later):

    {
      "version": 1,
      "next_id": 4,
      "tasks": [ {...task...}, ... ]
    }

Writes are atomic: data goes to a temporary file in the same directory which is
then ``os.replace``-d over the real file. A crash mid-write can therefore never
leave a half-written, corrupt JSON file behind.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import Priority, Task

FORMAT_VERSION = 1
DEFAULT_FILENAME = ".todo.json"


class StorageError(Exception):
    """Raised when the data file can't be read or parsed."""


def default_path() -> Path:
    """``$TODO_FILE`` if set, otherwise ``~/.todo.json``."""
    env = os.environ.get("TODO_FILE")
    return Path(env).expanduser() if env else Path.home() / DEFAULT_FILENAME


class TaskStore:
    """In-memory task list backed by a JSON file.

    Usage::

        store = TaskStore.load(path)
        store.add("Write report", priority=Priority.HIGH)
        store.save()
    """

    def __init__(self, path: Path, tasks: list[Task] | None = None, next_id: int = 1):
        self.path = Path(path)
        self.tasks: list[Task] = tasks or []
        # IDs are never reused, even after deletion, so a stale ID typed from
        # an old listing can't accidentally hit a different task.
        self.next_id = max(next_id, max((t.id for t in self.tasks), default=0) + 1)

    # ---- persistence ---------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "TaskStore":
        path = Path(path)
        if not path.exists():
            return cls(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StorageError(f"{path} is not valid JSON: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"can't read {path}: {exc}") from exc

        if not isinstance(raw, dict) or "tasks" not in raw:
            raise StorageError(f"{path} doesn't look like a todo file")
        version = raw.get("version", 1)
        if version > FORMAT_VERSION:
            raise StorageError(f"{path} uses format v{version}; this tool supports v{FORMAT_VERSION}")

        try:
            tasks = [Task.from_dict(d) for d in raw["tasks"]]
        except ValueError as exc:
            raise StorageError(str(exc)) from exc
        return cls(path, tasks, int(raw.get("next_id", 1)))

    def save(self) -> None:
        payload = {
            "version": FORMAT_VERSION,
            "next_id": self.next_id,
            "tasks": [t.to_dict() for t in self.tasks],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".todo-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)  # atomic on POSIX and Windows
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    # ---- operations ----------------------------------------------------

    def add(self, title: str, priority: Priority = Priority.MEDIUM, due=None, tags=None) -> Task:
        title = title.strip()
        if not title:
            raise ValueError("task title can't be empty")
        task = Task(id=self.next_id, title=title, priority=priority, due=due, tags=list(tags or []))
        self.tasks.append(task)
        self.next_id += 1
        return task

    def get(self, task_id: int) -> Task:
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise KeyError(f"no task with id {task_id}")

    def remove(self, task_id: int) -> Task:
        task = self.get(task_id)
        self.tasks.remove(task)
        return task

    def clear_done(self) -> list[Task]:
        """Delete all completed tasks; returns what was removed."""
        removed = [t for t in self.tasks if t.done]
        self.tasks = [t for t in self.tasks if not t.done]
        return removed
