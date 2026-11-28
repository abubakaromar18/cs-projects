"""Two Sudoku solvers, so their search effort can be compared.

``solve_naive``
    Classic depth-first backtracking: take the first empty cell, try 1-9,
    recurse, undo on failure. Correct but can explore millions of nodes.

``solve`` (the default)
    Backtracking *with constraint propagation*. Each cell keeps a 9-bit
    candidate mask. After every assignment we repeatedly apply two rules
    until nothing changes:

    1. **Naked single** - a cell with exactly one candidate must take it.
    2. **Hidden single** - if a digit fits in only one cell of a unit, it
       must go there.

    Propagation either fills the board, proves a contradiction (some cell
    has no candidates), or stalls. When it stalls we branch on the cell with
    the **fewest candidates** (the MRV heuristic) which keeps the search tree
    narrow. Most newspaper puzzles are solved with zero guesses.

Both functions return a :class:`Result` with the solution (or ``None``)
and statistics about the search.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Sequence

from .board import CELLS, PEERS, UNITS, is_valid

ALL = 0x1FF  # bits 0..8 set -> digits 1..9 all possible


def _bit(d: int) -> int:
    return 1 << (d - 1)


def _digits(mask: int) -> Iterator[int]:
    """Yield the digits whose bits are set in ``mask``."""
    d = 1
    while mask:
        if mask & 1:
            yield d
        mask >>= 1
        d += 1


def _popcount(mask: int) -> int:
    return bin(mask).count("1")


@dataclass
class Stats:
    nodes: int = 0          # recursive search calls
    guesses: int = 0        # branch points where we tried a value
    backtracks: int = 0     # guesses that led to a dead end
    propagated: int = 0     # cells filled by propagation rules


@dataclass
class Result:
    solution: list[int] | None
    stats: Stats = field(default_factory=Stats)

    @property
    def solved(self) -> bool:
        return self.solution is not None


class Contradiction(Exception):
    """Internal signal: the current partial assignment cannot be completed."""


# --------------------------------------------------------------------------
# Naive backtracking
# --------------------------------------------------------------------------

def solve_naive(puzzle: Sequence[int], max_nodes: int | None = None) -> Result:
    """Plain backtracking. ``max_nodes`` aborts very long searches (returns unsolved)."""
    stats = Stats()
    if not is_valid(puzzle):
        return Result(None, stats)
    board = list(puzzle)

    def ok(i: int, d: int) -> bool:
        return all(board[p] != d for p in PEERS[i])

    def search(start: int) -> bool:
        stats.nodes += 1
        if max_nodes is not None and stats.nodes > max_nodes:
            raise TimeoutError
        i = next((k for k in range(start, CELLS) if board[k] == 0), None)
        if i is None:
            return True
        for d in range(1, 10):
            if ok(i, d):
                stats.guesses += 1
                board[i] = d
                if search(i + 1):
                    return True
                board[i] = 0
                stats.backtracks += 1
        return False

    try:
        found = search(0)
    except TimeoutError:
        found = False
    return Result(board if found else None, stats)


# --------------------------------------------------------------------------
# Constraint propagation + MRV backtracking
# --------------------------------------------------------------------------

class _State:
    """Candidate masks for all 81 cells, plus the values placed so far."""

    __slots__ = ("cand", "values")

    def __init__(self, cand: list[int], values: list[int]):
        self.cand = cand
        self.values = values

    def copy(self) -> "_State":
        return _State(self.cand[:], self.values[:])

    def assign(self, i: int, d: int, stats: Stats) -> None:
        """Place ``d`` at ``i`` and propagate to a fixed point."""
        queue = [(i, d)]
        while queue:
            i, d = queue.pop()
            if self.values[i] == d:
                continue
            if self.values[i] or not self.cand[i] & _bit(d):
                raise Contradiction
            self.values[i] = d
            self.cand[i] = _bit(d)
            # Eliminate d from every peer; any peer reduced to one candidate
            # becomes a naked single and is queued.
            b = _bit(d)
            for p in PEERS[i]:
                if self.cand[p] & b:
                    if self.values[p]:
                        raise Contradiction
                    self.cand[p] &= ~b
                    m = self.cand[p]
                    if m == 0:
                        raise Contradiction
                    if m & (m - 1) == 0:  # exactly one bit left
                        queue.append((p, m.bit_length()))
                        stats.propagated += 1
            if not queue:
                queue.extend(self._hidden_singles(stats))

    def _hidden_singles(self, stats: Stats) -> list[tuple[int, int]]:
        """Find digits that have only one possible home in some unit."""
        found: list[tuple[int, int]] = []
        for unit in UNITS:
            for d in range(1, 10):
                b = _bit(d)
                spots = [i for i in unit if self.cand[i] & b]
                if not spots:
                    raise Contradiction  # digit has nowhere to go
                if len(spots) == 1 and not self.values[spots[0]]:
                    found.append((spots[0], d))
        stats.propagated += len(found)
        return found

    def best_cell(self) -> int | None:
        """MRV: the unfilled cell with the fewest candidates (None if full)."""
        best, best_n = None, 10
        for i in range(CELLS):
            if not self.values[i]:
                n = _popcount(self.cand[i])
                if n < best_n:
                    best, best_n = i, n
                    if n == 2:
                        break
        return best


def _initial_state(puzzle: Sequence[int], stats: Stats) -> _State:
    state = _State([ALL] * CELLS, [0] * CELLS)
    for i, v in enumerate(puzzle):
        if v:
            state.assign(i, v, stats)
    return state


def _search(state: _State, stats: Stats) -> Iterator[list[int]]:
    """Depth-first search yielding every solution reachable from ``state``."""
    stats.nodes += 1
    i = state.best_cell()
    if i is None:
        yield state.values[:]
        return
    for d in _digits(state.cand[i]):
        stats.guesses += 1
        child = state.copy()
        try:
            child.assign(i, d, stats)
        except Contradiction:
            stats.backtracks += 1
            continue
        yield from _search(child, stats)


def solutions(puzzle: Sequence[int], stats: Stats | None = None) -> Iterator[list[int]]:
    """Lazily yield all solutions of ``puzzle``."""
    stats = stats if stats is not None else Stats()
    if len(puzzle) != CELLS or not is_valid(puzzle):
        return
    try:
        state = _initial_state(puzzle, stats)
    except Contradiction:
        return
    yield from _search(state, stats)


def solve(puzzle: Sequence[int]) -> Result:
    """Solve with constraint propagation and MRV. Returns the first solution."""
    stats = Stats()
    sol = next(solutions(puzzle, stats), None)
    return Result(sol, stats)


def count_solutions(puzzle: Sequence[int], limit: int = 2) -> int:
    """Count solutions, stopping at ``limit`` (2 is enough to test uniqueness)."""
    n = 0
    for _ in solutions(puzzle):
        n += 1
        if n >= limit:
            break
    return n


def has_unique_solution(puzzle: Sequence[int]) -> bool:
    return count_solutions(puzzle, limit=2) == 1


def candidates(puzzle: Sequence[int]) -> list[set[int]]:
    """Pencil marks after propagation (useful for hints). Empty list if contradictory."""
    try:
        state = _initial_state(puzzle, Stats())
    except Contradiction:
        return []
    return [set(_digits(m)) for m in state.cand]


__all__ = [
    "Result",
    "Stats",
    "solve",
    "solve_naive",
    "solutions",
    "count_solutions",
    "has_unique_solution",
    "candidates",
]
