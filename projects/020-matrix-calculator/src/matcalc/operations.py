"""Core linear-algebra algorithms with optional step-by-step logs.

Everything here is built on Gauss–Jordan elimination over exact rationals:

* :func:`rref`        reduced row echelon form, pivot columns and rank
* :func:`determinant` via forward elimination (O(n^3)), tracking how each
                      row operation changes the determinant
* :func:`determinant_cofactor` the textbook Laplace expansion (O(n!)),
                      kept as an independent cross-check
* :func:`inverse`     by row-reducing the augmented matrix [A | I]
* :func:`solve`       a linear system Ax = b, classifying it as unique,
                      infinite or inconsistent
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .matrix import Matrix, fmt
from .steps import Grid, StepLog


class SingularMatrixError(ValueError):
    """Raised when an inverse is requested for a matrix with determinant 0."""


# ---------------------------------------------------------------------------
# Reduced row echelon form
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RREFResult:
    matrix: Matrix
    pivots: tuple[int, ...]
    steps: StepLog

    @property
    def rank(self) -> int:
        return len(self.pivots)


def _choose_pivot(grid: Grid, col: int, start: int) -> int | None:
    """First row at or below ``start`` with a non-zero entry in ``col``.

    With exact arithmetic we don't need partial pivoting for numerical
    stability, so we prefer an entry equal to ±1 when one exists: it avoids
    introducing fractions and keeps the printed steps readable.
    """
    candidates = [r for r in range(start, len(grid)) if grid[r][col] != 0]
    if not candidates:
        return None
    for r in candidates:
        if abs(grid[r][col]) == 1:
            return r
    return candidates[0]


def _gauss_jordan(grid: Grid, log: StepLog, ncols: int | None = None) -> list[int]:
    """Row-reduce ``grid`` in place to RREF; returns pivot columns.

    Only the first ``ncols`` columns are used to pick pivots, which lets us
    reduce an augmented matrix [A | B] while treating B as passenger columns.
    """
    nrows = len(grid)
    ncols = len(grid[0]) if ncols is None else ncols
    pivots: list[int] = []
    r = 0
    for c in range(ncols):
        if r == nrows:
            break
        p = _choose_pivot(grid, c, r)
        if p is None:
            continue  # free column
        if p != r:
            log.swap(grid, r, p)
        if grid[r][c] != 1:
            log.scale(grid, r, 1 / grid[r][c])
        # Clear the column above and below the pivot.
        for i in range(nrows):
            if i != r and grid[i][c] != 0:
                log.add_multiple(grid, i, r, -grid[i][c])
        pivots.append(c)
        r += 1
    return pivots


def rref(m: Matrix, *, steps: bool = True) -> RREFResult:
    grid = m.tolist()
    log = StepLog(enabled=steps)
    log.note(grid, "Start")
    pivots = _gauss_jordan(grid, log)
    return RREFResult(Matrix(grid), tuple(pivots), log)


def rank(m: Matrix) -> int:
    return rref(m, steps=False).rank


# ---------------------------------------------------------------------------
# Determinant
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DeterminantResult:
    value: Fraction
    steps: StepLog
    explanation: str


def determinant(m: Matrix, *, steps: bool = True) -> DeterminantResult:
    """Reduce to upper-triangular form, then multiply the diagonal.

    Row swaps flip the sign and adding a multiple of a row leaves the
    determinant unchanged, so det(A) = (-1)^swaps * product(diagonal).
    We never scale rows here, which keeps that bookkeeping trivial.
    """
    if not m.is_square:
        raise ValueError("determinant is only defined for square matrices")
    n = m.rows
    grid = m.tolist()
    log = StepLog(enabled=steps)
    log.note(grid, "Start")
    swaps = 0
    for c in range(n):
        p = _choose_pivot(grid, c, c)
        if p is None:
            explanation = (
                f"Column {c + 1} has no non-zero pivot on or below the diagonal, "
                "so the matrix is singular and det = 0."
            )
            return DeterminantResult(Fraction(0), log, explanation)
        if p != c:
            log.swap(grid, c, p)
            swaps += 1
        for i in range(c + 1, n):
            if grid[i][c] != 0:
                log.add_multiple(grid, i, c, -grid[i][c] / grid[c][c])

    diagonal = [grid[i][i] for i in range(n)]
    value = Fraction(1)
    for d in diagonal:
        value *= d
    sign = -1 if swaps % 2 else 1
    value *= sign
    product = " * ".join(f"({fmt(d)})" if d < 0 else fmt(d) for d in diagonal)
    explanation = (
        f"Upper-triangular after {swaps} row swap(s); "
        f"det = {'-' if sign < 0 else ''}({product}) = {fmt(value)}"
    )
    return DeterminantResult(value, log, explanation)


def determinant_cofactor(m: Matrix) -> Fraction:
    """Laplace expansion along the first row. Exponential, but obviously correct."""
    if not m.is_square:
        raise ValueError("determinant is only defined for square matrices")
    if m.rows == 1:
        return m[0, 0]
    if m.rows == 2:
        return m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0]
    total = Fraction(0)
    for j in range(m.cols):
        if m[0, j] != 0:
            sign = -1 if j % 2 else 1
            total += sign * m[0, j] * determinant_cofactor(m.minor(0, j))
    return total


# ---------------------------------------------------------------------------
# Inverse
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InverseResult:
    matrix: Matrix
    steps: StepLog


def inverse_with_steps(m: Matrix, *, steps: bool = True) -> InverseResult:
    """Row-reduce [A | I]. If the left half becomes I, the right half is A^-1."""
    if not m.is_square:
        raise ValueError("only square matrices can be inverted")
    n = m.rows
    grid = m.augment(Matrix.identity(n)).tolist()
    log = StepLog(divider=n, enabled=steps)
    log.note(grid, "Start with [A | I]")
    pivots = _gauss_jordan(grid, log, ncols=n)
    if len(pivots) < n:
        raise SingularMatrixError(
            f"matrix is singular (rank {len(pivots)} < {n}); it has no inverse"
        )
    return InverseResult(Matrix(row[n:] for row in grid), log)


def inverse(m: Matrix) -> Matrix:
    return inverse_with_steps(m, steps=False).matrix


# ---------------------------------------------------------------------------
# Linear systems
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Solution:
    kind: str  # "unique", "infinite" or "none"
    particular: tuple[Fraction, ...] | None
    free_vars: tuple[int, ...]
    rref: RREFResult

    def describe(self) -> str:
        if self.kind == "none":
            return "The system is inconsistent: a row reads 0 = non-zero. No solution."
        assert self.particular is not None
        lines = []
        nvars = len(self.particular)
        pivots = self.rref.pivots
        grid = self.rref.matrix
        for v in range(nvars):
            if v in self.free_vars:
                lines.append(f"x{v + 1} = t{v + 1}  (free)")
                continue
            r = pivots.index(v)
            expr = fmt(grid[r, nvars])
            for f in self.free_vars:
                coef = -grid[r, f]
                if coef != 0:
                    sign = "+" if coef > 0 else "-"
                    mag = "" if abs(coef) == 1 else fmt(abs(coef))
                    expr += f" {sign} {mag}t{f + 1}"
            lines.append(f"x{v + 1} = {expr}")
        header = (
            "Unique solution:"
            if self.kind == "unique"
            else f"Infinitely many solutions ({len(self.free_vars)} free variable(s)):"
        )
        return "\n".join([header, *("  " + line for line in lines)])


def solve(a: Matrix, b: Matrix, *, steps: bool = True) -> Solution:
    """Solve Ax = b by reducing the augmented matrix [A | b]."""
    if b.cols != 1 or b.rows != a.rows:
        raise ValueError("b must be a column vector with as many rows as A")
    nvars = a.cols
    grid = a.augment(b).tolist()
    log = StepLog(divider=nvars, enabled=steps)
    log.note(grid, "Start with [A | b]")
    pivots = _gauss_jordan(grid, log, ncols=nvars)
    result = RREFResult(Matrix(grid), tuple(pivots), log)

    # A row [0 0 ... 0 | c] with c != 0 means 0 = c: inconsistent.
    if any(all(x == 0 for x in row[:nvars]) and row[nvars] != 0 for row in grid):
        return Solution("none", None, (), result)

    free = tuple(c for c in range(nvars) if c not in pivots)
    particular = [Fraction(0)] * nvars  # free variables set to 0
    for r, c in enumerate(pivots):
        particular[c] = grid[r][nvars]
    kind = "unique" if not free else "infinite"
    return Solution(kind, tuple(particular), free, result)
