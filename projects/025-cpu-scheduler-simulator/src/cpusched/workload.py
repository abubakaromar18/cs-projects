"""Load workloads from CSV text: ``pid,arrival,burst`` per line.

Blank lines and ``#`` comments are ignored, and an optional header row
(``pid,arrival,burst``) is skipped. Example::

    # pid,arrival,burst
    P1,0,8
    P2,1,4
"""

from __future__ import annotations

import random
from pathlib import Path

from .models import Process, validate_processes


def parse_workload(text: str) -> list[Process]:
    processes = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        fields = [f.strip() for f in line.split(",")]
        if fields[0].lower() == "pid":  # header row
            continue
        if len(fields) != 3:
            raise ValueError(f"line {lineno}: expected 'pid,arrival,burst', got {raw!r}")
        pid, arrival, burst = fields
        try:
            processes.append(Process(pid, int(arrival), int(burst)))
        except ValueError as exc:
            raise ValueError(f"line {lineno}: {exc}") from None
    return validate_processes(processes)


def load_workload(path: str | Path) -> list[Process]:
    return parse_workload(Path(path).read_text(encoding="utf-8"))


def random_workload(n: int, seed: int | None = None, max_arrival: int = 20,
                    max_burst: int = 10) -> list[Process]:
    """Generate ``n`` random processes (reproducible with ``seed``)."""
    if n <= 0:
        raise ValueError("n must be > 0")
    rng = random.Random(seed)
    return [Process(f"P{i + 1}", rng.randint(0, max_arrival), rng.randint(1, max_burst))
            for i in range(n)]
