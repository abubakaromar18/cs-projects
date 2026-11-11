"""JSON persistence. Only (word, frequency) pairs are stored; the tree is rebuilt on load."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .trie import Trie


def save(trie: Trie, path: str | Path) -> None:
    """Write atomically: dump to a temp file in the same dir, then rename over."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(trie.to_dict(), f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load(path: str | Path) -> Trie:
    path = Path(path)
    if not path.exists():
        return Trie()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("words", {}), dict):
        raise ValueError(f"{path}: not a trie file")
    return Trie.from_dict(data)
