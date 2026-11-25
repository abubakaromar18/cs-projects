"""Interval functions decide *which* runs of pixels get sorted.

Each function receives a 2-D float array of key values (rows x cols) and
returns a boolean mask of the same shape. A contiguous run of True values
within a row is one "interval"; each interval is sorted independently, and
False pixels stay exactly where they are. That contrast — sorted streaks
next to untouched detail — is what makes pixel sorting look like glitch art.
"""

from __future__ import annotations

import numpy as np


def full(values: np.ndarray, **_: object) -> np.ndarray:
    """Sort every row end to end."""
    return np.ones(values.shape, dtype=bool)


def threshold(values: np.ndarray, lower: float = 0.25, upper: float = 0.8, **_: object) -> np.ndarray:
    """Sort only pixels whose key lies in [lower, upper] (Kim Asendorf style)."""
    if not 0.0 <= lower <= upper <= 1.0:
        raise ValueError("need 0 <= lower <= upper <= 1")
    return (values >= lower) & (values <= upper)


def edges(values: np.ndarray, edge_threshold: float = 0.1, **_: object) -> np.ndarray:
    """Break intervals wherever the key changes sharply (a 1-D edge detector).

    Pixels on an edge become boundaries (False), so sorting stays inside
    regions of similar value and preserves object outlines.
    """
    grad = np.zeros(values.shape)
    grad[:, 1:] = np.abs(np.diff(values, axis=1))
    return grad < edge_threshold


def random_runs(values: np.ndarray, mean_length: int = 40, seed: int | None = None, **_: object) -> np.ndarray:
    """Split rows into intervals of random (geometric) length.

    A boundary is placed at each pixel with probability 1/mean_length, so run
    lengths follow a geometric distribution with the requested mean.
    """
    if mean_length < 1:
        raise ValueError("mean_length must be >= 1")
    rng = np.random.default_rng(seed)
    return rng.random(values.shape) >= 1.0 / mean_length


INTERVALS = {
    "full": full,
    "threshold": threshold,
    "edges": edges,
    "random": random_runs,
}


def get_interval(name: str):
    try:
        return INTERVALS[name]
    except KeyError:
        raise ValueError(f"unknown interval {name!r}; choose from {sorted(INTERVALS)}") from None


def runs(mask_row: np.ndarray) -> list[tuple[int, int]]:
    """Return [start, end) index pairs of contiguous True runs in a 1-D mask.

    Uses the classic trick of diffing a zero-padded int array: +1 marks a
    run start and -1 marks one past a run end. O(n), no Python-level loop.
    """
    padded = np.concatenate(([0], mask_row.astype(np.int8), [0]))
    d = np.diff(padded)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return list(zip(starts.tolist(), ends.tolist()))
