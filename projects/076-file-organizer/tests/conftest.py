import os
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def make_files(tmp_path):
    """Create files under tmp_path. Values are optional (year, month) mtimes."""

    def _make(spec):
        for rel, date in spec.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"content of {rel}")
            if date:
                ts = datetime(date[0], date[1], 15, 12, 0).timestamp()
                os.utime(path, (ts, ts))
        return tmp_path

    return _make


def tree(root: Path) -> set[str]:
    """All files under root as posix relative paths, journal excluded."""
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not p.name.startswith(".fileorg-journal")
    }
