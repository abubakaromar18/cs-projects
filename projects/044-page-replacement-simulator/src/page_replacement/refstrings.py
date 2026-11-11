"""Reference strings: parsing user input and generating synthetic workloads."""

from __future__ import annotations

import random
import re

# Silberschatz, *Operating System Concepts* — the canonical example.
# With 3 frames: FIFO = 15 faults, LRU = 12, OPT = 9.
TEXTBOOK = (7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1)

# The string Belady used to show FIFO can fault MORE with more memory:
# 3 frames -> 9 faults, 4 frames -> 10 faults.
BELADY = (1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5)

PRESETS = {"textbook": TEXTBOOK, "belady": BELADY}


def parse(text: str) -> tuple[int, ...]:
    """Parse ``"7 0 1, 2"`` (any mix of commas/whitespace) into page numbers."""
    tokens = [tok for tok in re.split(r"[\s,]+", text.strip()) if tok]
    if not tokens:
        raise ValueError("reference string is empty")
    try:
        pages = tuple(int(tok) for tok in tokens)
    except ValueError as exc:
        raise ValueError(f"page numbers must be integers: {exc}") from None
    if any(p < 0 for p in pages):
        raise ValueError("page numbers must be non-negative")
    return pages


def uniform(length: int, pages: int, seed: int | None = None) -> tuple[int, ...]:
    """Every reference picks a page uniformly at random — no locality, so all
    online policies perform about the same (badly)."""
    rng = random.Random(seed)
    return tuple(rng.randrange(pages) for _ in range(length))


def locality(
    length: int,
    pages: int,
    working_set: int = 4,
    phase: int = 25,
    jump: float = 0.1,
    seed: int | None = None,
) -> tuple[int, ...]:
    """Model *temporal locality*: the program works within a small working set
    of pages for a phase, then moves on. Within a phase, a fraction ``jump`` of
    references stray outside the working set.

    This is the kind of workload where LRU and Clock pull ahead of FIFO.
    """
    if not 1 <= working_set <= pages:
        raise ValueError("working_set must be between 1 and pages")
    rng = random.Random(seed)
    out: list[int] = []
    while len(out) < length:
        base = rng.randrange(pages)
        ws = [(base + i) % pages for i in range(working_set)]
        for _ in range(min(phase, length - len(out))):
            out.append(rng.randrange(pages) if rng.random() < jump else rng.choice(ws))
    return tuple(out)


def loop(length: int, pages: int) -> tuple[int, ...]:
    """A sequential scan repeated: 0 1 2 ... n-1 0 1 2 ...

    The pathological case for LRU: with fewer frames than ``pages`` it evicts
    exactly the page needed next, so *every* reference faults.
    """
    return tuple(i % pages for i in range(length))
