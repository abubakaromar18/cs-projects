"""Most-recently-used color history with JSON persistence."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Iterator

from .colors import RGB


class History:
    """A bounded MRU list: re-adding a color moves it to the front."""

    def __init__(self, capacity: int = 16, path: Path | None = None) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self.path = path
        self._items: deque[RGB] = deque(maxlen=capacity)

    def add(self, color: RGB) -> None:
        try:
            self._items.remove(color)  # O(n) but n is tiny
        except ValueError:
            pass
        self._items.appendleft(color)  # deque(maxlen) drops the oldest

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self) -> Iterator[RGB]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, i: int) -> RGB:
        return self._items[i]

    # ---------- persistence ----------
    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([c.hex for c in self._items], indent=2))
        tmp.replace(self.path)  # atomic on POSIX and Windows

    def load(self) -> None:
        """Load from disk, silently ignoring a missing or corrupt file."""
        if self.path is None or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            colors = [RGB.from_hex(h) for h in data if isinstance(h, str)]
        except (ValueError, OSError):
            return
        self._items.clear()
        for c in reversed(colors[: self.capacity]):
            self.add(c)


def default_history_path() -> Path:
    return Path.home() / ".config" / "colorpick" / "history.json"
