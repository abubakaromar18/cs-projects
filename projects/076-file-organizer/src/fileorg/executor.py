"""Apply a plan to disk, recording a journal so every run can be undone."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .planner import JOURNAL_NAME, Plan


@dataclass
class Result:
    moved: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    journal: Path | None = None


def _remove_empty_parents(path: Path, stop: Path) -> None:
    """Delete now-empty directories from ``path`` up to (not including) ``stop``."""
    current = path
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            return  # not empty (or not ours to remove)
        current = current.parent


def apply_plan(plan: Plan, dry_run: bool = False) -> Result:
    """Execute ``plan``. With ``dry_run`` nothing on disk changes.

    Each completed move is appended to the journal *before* the next one
    starts, so even an interrupted run leaves an accurate record for undo.
    """
    result = Result()
    if dry_run or not plan.moves:
        return result

    journal_path = plan.root / JOURNAL_NAME
    history = _read_journal(journal_path)
    run = {"started": datetime.now(timezone.utc).isoformat(), "moves": []}
    history.append(run)

    for move in plan.moves:
        src, dst = move.relative(plan.root)
        try:
            if move.dst.exists():
                # Something appeared since planning; never overwrite.
                raise FileExistsError(f"destination exists: {dst}")
            move.dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(move.src), str(move.dst))
        except OSError as exc:
            result.errors.append((src, str(exc)))
            continue
        run["moves"].append({"src": src, "dst": dst})
        result.moved += 1
        _write_journal(journal_path, history)
        _remove_empty_parents(move.src.parent, plan.root)

    if not run["moves"]:
        history.pop()
    if history:
        _write_journal(journal_path, history)
        result.journal = journal_path
    return result


def undo(root: str | Path) -> Result:
    """Reverse the most recent run recorded in ``root``'s journal."""
    root = Path(root).resolve()
    journal_path = root / JOURNAL_NAME
    history = _read_journal(journal_path)
    result = Result(journal=journal_path)
    if not history:
        return result

    run = history.pop()
    # Undo in reverse order so chains of moves unwind correctly.
    remaining = []
    for entry in reversed(run["moves"]):
        src, dst = root / entry["src"], root / entry["dst"]
        try:
            if src.exists():
                raise FileExistsError(f"original location is occupied: {entry['src']}")
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
        except OSError as exc:
            result.errors.append((entry["dst"], str(exc)))
            remaining.append(entry)
            continue
        result.moved += 1
        _remove_empty_parents(dst.parent, root)

    if remaining:  # keep what we could not undo so the user can retry
        run["moves"] = list(reversed(remaining))
        history.append(run)
    if history:
        _write_journal(journal_path, history)
    else:
        journal_path.unlink(missing_ok=True)
    return result


def _read_journal(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"corrupt journal: {path}")
    return data


def _write_journal(path: Path, history: list[dict]) -> None:
    # Write to a temp file then rename: the journal is never half-written.
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, indent=2), encoding="utf-8")
    tmp.replace(path)
