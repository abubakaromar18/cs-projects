"""Recording the elementary row operations performed by an algorithm.

Algorithms in :mod:`matcalc.operations` work on a plain ``list[list[Fraction]]``
buffer and call into a :class:`StepLog` every time they change it. The log
keeps a human-readable description plus a snapshot of the matrix after the
operation, which is exactly what a student writes on paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .matrix import fmt, render

Grid = list[list[Fraction]]


@dataclass(frozen=True)
class Step:
    """One elementary row operation and the matrix it produced."""

    description: str
    snapshot: tuple[tuple[Fraction, ...], ...]
    divider: int | None = None

    def __str__(self) -> str:
        return f"{self.description}\n{render(self.snapshot, self.divider)}"


@dataclass
class StepLog:
    """Applies row operations to a grid and records each one.

    The three elementary row operations are:

    * swap two rows                       R_i <-> R_j
    * scale a row by a non-zero constant  R_i <- k * R_i
    * add a multiple of one row to another R_i <- R_i + k * R_j

    Each has a known effect on the determinant (negate, multiply by k,
    unchanged), which :func:`matcalc.operations.determinant` relies on.
    """

    divider: int | None = None
    enabled: bool = True
    steps: list[Step] = field(default_factory=list)

    def note(self, grid: Grid, description: str) -> None:
        if self.enabled:
            snap = tuple(tuple(row) for row in grid)
            self.steps.append(Step(description, snap, self.divider))

    def swap(self, grid: Grid, i: int, j: int) -> None:
        grid[i], grid[j] = grid[j], grid[i]
        self.note(grid, f"R{i + 1} <-> R{j + 1}")

    def scale(self, grid: Grid, i: int, k: Fraction) -> None:
        if k == 0:
            raise ValueError("scaling a row by 0 is not an elementary operation")
        grid[i] = [k * x for x in grid[i]]
        self.note(grid, f"R{i + 1} <- {_coef(k)}R{i + 1}")

    def add_multiple(self, grid: Grid, target: int, source: int, k: Fraction) -> None:
        if k == 0:
            return
        grid[target] = [a + k * b for a, b in zip(grid[target], grid[source])]
        sign = "+" if k > 0 else "-"
        self.note(
            grid, f"R{target + 1} <- R{target + 1} {sign} {_coef(abs(k))}R{source + 1}"
        )

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    def render(self) -> str:
        return "\n\n".join(f"Step {n}: {s}" for n, s in enumerate(self.steps, 1))


def _coef(k: Fraction) -> str:
    """Render a coefficient for an operation label: 1 -> '', 1/2 -> '(1/2)'."""
    if k == 1:
        return ""
    if k == -1:
        return "-"
    text = fmt(k)
    return f"({text})" if "/" in text or text.startswith("-") else text
