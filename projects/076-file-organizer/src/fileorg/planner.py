"""Turn a directory listing into a plan of moves, without touching the disk.

The planner is deterministic: files are visited in sorted order, and name
collisions are resolved the same way every time, so a dry run and the real
run always agree.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterator

from .rules import Rules, extension_of

JOURNAL_NAME = ".fileorg-journal.json"
JOURNAL_TMP = ".fileorg-journal.tmp"


class Mode(str, Enum):
    TYPE = "type"          # Images/photo.jpg
    DATE = "date"          # 2026/11/photo.jpg
    TYPE_DATE = "type-date"  # Images/2026/11/photo.jpg


@dataclass(frozen=True)
class Move:
    src: Path
    dst: Path

    def relative(self, root: Path) -> tuple[str, str]:
        return (str(self.src.relative_to(root)), str(self.dst.relative_to(root)))


@dataclass
class Plan:
    root: Path
    moves: list[Move] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        """Count planned moves per top-level destination folder."""
        counts: dict[str, int] = {}
        for move in self.moves:
            top = move.dst.relative_to(self.root).parts[0]
            counts[top] = counts.get(top, 0) + 1
        return dict(sorted(counts.items()))


def _iter_files(root: Path, recursive: bool, include_hidden: bool,
                protected: set[str], plan: Plan) -> Iterator[Path]:
    """Yield candidate files under ``root`` in a stable order.

    Top-level folders whose names are destination folders (``protected``) are
    never descended into, so running the organizer twice is a no-op.
    """
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name)
        except PermissionError:
            plan.skipped.append((current, "permission denied"))
            continue
        subdirs: list[Path] = []
        for entry in entries:
            path = Path(entry.path)
            hidden = entry.name.startswith(".")
            if entry.name in (JOURNAL_NAME, JOURNAL_TMP):
                continue
            if hidden and not include_hidden:
                continue
            if entry.is_symlink():
                plan.skipped.append((path, "symlink"))
                continue
            if entry.is_dir():
                if recursive and not (current == root and entry.name in protected):
                    subdirs.append(path)
                continue
            if entry.is_file():
                yield path
        # Reverse so that popping visits subdirectories in sorted order.
        stack.extend(reversed(subdirs))


def _date_parts(path: Path) -> tuple[str, str]:
    ts = path.stat().st_mtime
    dt = datetime.fromtimestamp(ts)
    return f"{dt.year:04d}", f"{dt.month:02d}"


def _target_dir(root: Path, path: Path, mode: Mode, rules: Rules) -> Path:
    if mode is Mode.TYPE:
        return root / rules.classify(path.name)
    year, month = _date_parts(path)
    if mode is Mode.DATE:
        return root / year / month
    return root / rules.classify(path.name) / year / month


def unique_name(directory: Path, name: str, taken: set[Path]) -> Path:
    """Return ``directory/name``, or ``name (1).ext``, ``name (2).ext``, ...

    ``taken`` holds destinations already claimed by earlier moves in the plan,
    so two source files with the same name never collide with each other.
    """
    candidate = directory / name
    if candidate not in taken and not candidate.exists():
        return candidate
    ext = extension_of(name)
    # Keep the original casing of the extension: "photo.JPG" -> "photo (1).JPG".
    stem = name[: -(len(ext) + 1)] if ext else name
    suffix = name[len(stem):]
    n = 1
    while True:
        candidate = directory / f"{stem} ({n}){suffix}"
        if candidate not in taken and not candidate.exists():
            return candidate
        n += 1


def plan_moves(root: str | Path, rules: Rules | None = None, mode: Mode | str = Mode.TYPE,
               recursive: bool = False, include_hidden: bool = False) -> Plan:
    """Build the list of moves that would organize ``root``."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    rules = rules or Rules()
    mode = Mode(mode)
    plan = Plan(root=root)

    # Folder names the organizer creates at the top level. Years count too
    # in date modes, but we cannot know them all in advance, so we treat any
    # 4-digit folder name as protected.
    protected = set(rules.folder_names) if mode is not Mode.DATE else set()
    if mode is Mode.DATE:
        protected |= {e.name for e in os.scandir(root)
                      if e.is_dir() and len(e.name) == 4 and e.name.isdigit()}

    taken: set[Path] = set()
    for path in _iter_files(root, recursive, include_hidden, protected, plan):
        target_dir = _target_dir(root, path, mode, rules)
        if path.parent == target_dir:
            continue  # already in the right place
        dst = unique_name(target_dir, path.name, taken)
        taken.add(dst)
        plan.moves.append(Move(path, dst))
    return plan
