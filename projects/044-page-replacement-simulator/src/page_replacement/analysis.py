"""Experiments across frame counts: fault curves and Belady's anomaly."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Sequence

from .policies import Page
from .simulator import simulate


def sweep(
    refs: Sequence[Page], algorithms: Iterable[str], frame_counts: Iterable[int]
) -> dict[str, dict[int, int]]:
    """Fault count for every (algorithm, frames) pair: ``{algo: {k: faults}}``."""
    counts = list(frame_counts)
    return {
        algo: {k: simulate(refs, k, algo, record=False).faults for k in counts}
        for algo in algorithms
    }


@dataclass(frozen=True)
class Anomaly:
    """More frames produced more faults."""

    algorithm: str
    frames: int  # k
    faults: int  # faults with k frames
    more_frames: int  # k' > k
    more_faults: int  # faults with k' frames (> faults)


def find_anomalies(curves: dict[str, dict[int, int]]) -> list[Anomaly]:
    """Every adjacent pair of frame counts where the fault curve goes *up*."""
    found = []
    for algo, curve in curves.items():
        ks = sorted(curve)
        for a, b in zip(ks, ks[1:]):
            if curve[b] > curve[a]:
                found.append(Anomaly(algo, a, curve[a], b, curve[b]))
    return found


def search_belady(
    algorithm: str = "fifo",
    *,
    length: int = 20,
    pages: int = 6,
    max_frames: int = 5,
    tries: int = 10_000,
    seed: int | None = None,
) -> tuple[tuple[int, ...], Anomaly] | None:
    """Randomly search for a reference string on which ``algorithm`` shows
    Belady's anomaly. For FIFO they are rare (well under 1% of random
    strings), so the search needs thousands of tries. LRU and OPT never show
    one, because they are *stack algorithms*: the set of pages resident with
    k frames is always a subset of those resident with k+1 frames.
    """
    rng = random.Random(seed)
    frames = range(1, max_frames + 1)
    for _ in range(tries):
        refs = tuple(rng.randrange(pages) for _ in range(length))
        anomalies = find_anomalies(sweep(refs, [algorithm], frames))
        if anomalies:
            return refs, anomalies[0]
    return None


def is_stack_inclusive(refs: Sequence[Page], algorithm: str, max_frames: int) -> bool:
    """Check the *inclusion property* directly: at every time step, the pages
    resident with k frames are a subset of those resident with k+1 frames.
    Holds for LRU and OPT; it is exactly what rules out Belady's anomaly."""
    runs = [simulate(refs, k, algorithm) for k in range(1, max_frames + 1)]
    for t in range(len(refs)):
        for small, big in zip(runs, runs[1:]):
            a = {p for p in small.steps[t].frames if p is not None}
            b = {p for p in big.steps[t].frames if p is not None}
            if not a <= b:
                return False
    return True
