"""Generate puzzles that have exactly one solution.

Approach:
1. Build a random complete grid by running the solver on an empty board
   with shuffled digit order (via a randomly seeded first row).
2. Visit cells in random order and blank each one, keeping the removal only
   if the puzzle still has a unique solution (checked with
   :func:`count_solutions` limited to 2).

Removing in symmetric pairs gives the classic "newspaper" look.
"""

from __future__ import annotations

import random

from .board import CELLS
from .solver import count_solutions, solve


def random_solution(rng: random.Random) -> list[int]:
    """A uniformly shuffled first row, then let the solver complete it.

    The relabelling step (permuting digits) plus shuffling rows within bands
    gives plenty of variety for practice puzzles.
    """
    seed = [0] * CELLS
    seed[:9] = rng.sample(range(1, 10), 9)
    grid = solve(seed).solution
    assert grid is not None  # any valid first row is completable
    # Shuffle rows inside each band and the bands themselves - both preserve validity.
    bands = [rng.sample(range(b * 3, b * 3 + 3), 3) for b in range(3)]
    rng.shuffle(bands)
    rows = [r for band in bands for r in band]
    return [grid[r * 9 + c] for r in rows for c in range(9)]


def generate(seed: int | None = None, min_givens: int = 24, symmetric: bool = True) -> tuple[list[int], list[int]]:
    """Return ``(puzzle, solution)``. Stops removing once ``min_givens`` remain."""
    rng = random.Random(seed)
    solution = random_solution(rng)
    puzzle = solution[:]
    order = list(range(CELLS))
    rng.shuffle(order)
    givens = CELLS
    for i in order:
        if givens <= min_givens:
            break
        pair = {i, CELLS - 1 - i} if symmetric else {i}
        if any(puzzle[j] == 0 for j in pair) or givens - len(pair) < min_givens:
            continue
        saved = {j: puzzle[j] for j in pair}
        for j in pair:
            puzzle[j] = 0
        if count_solutions(puzzle, limit=2) == 1:
            givens -= len(pair)
        else:
            for j, v in saved.items():
                puzzle[j] = v
    return puzzle, solution
