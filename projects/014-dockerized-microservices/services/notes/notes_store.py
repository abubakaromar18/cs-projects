"""Persistent note storage for the notes service.

Notes live in a single JSON file in DATA_DIR. In Docker Compose that
directory is the named volume `notes-data`, so notes survive
`docker compose down` and are only removed by `docker compose down -v`.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_TITLE = 200
MAX_BODY = 10_000


class ValidationError(ValueError):
    """Raised when a client sends a note that breaks the rules."""


@dataclass
class Note:
    id: int
    title: str
    body: str
    created_at: str


def validate(data: object) -> tuple[str, str]:
    """Return a clean (title, body) pair or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError("expected a JSON object")
    title = data.get("title")
    body = data.get("body", "")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("title is required")
    if not isinstance(body, str):
        raise ValidationError("body must be a string")
    if len(title) > MAX_TITLE:
        raise ValidationError(f"title is longer than {MAX_TITLE} characters")
    if len(body) > MAX_BODY:
        raise ValidationError(f"body is longer than {MAX_BODY} characters")
    return title.strip(), body


class NoteStore:
    """Thread-safe CRUD store backed by an atomically rewritten JSON file."""

    def __init__(self, data_dir: str | os.PathLike) -> None:
        self.path = Path(data_dir) / "notes.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._notes: dict[int, Note] = {}
        self._next_id = 1
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._notes = {n["id"]: Note(**n) for n in raw.get("notes", [])}
        # Never reuse an id, even after the newest note is deleted.
        self._next_id = max(raw.get("next_id", 1), max(self._notes, default=0) + 1)

    def _save(self) -> None:
        payload = {
            "next_id": self._next_id,
            "notes": [asdict(n) for n in self._notes.values()],
        }
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.path)  # atomic on POSIX

    def create(self, title: str, body: str) -> Note:
        with self._lock:
            note = Note(
                id=self._next_id,
                title=title,
                body=body,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            self._notes[note.id] = note
            self._next_id += 1
            self._save()
            return note

    def get(self, note_id: int) -> Note | None:
        with self._lock:
            return self._notes.get(note_id)

    def list(self) -> list[Note]:
        with self._lock:
            return sorted(self._notes.values(), key=lambda n: n.id)

    def delete(self, note_id: int) -> bool:
        with self._lock:
            if self._notes.pop(note_id, None) is None:
                return False
            self._save()
            return True
