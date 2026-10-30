"""An immutable matrix of exact rational numbers.

Every entry is stored as a :class:`fractions.Fraction`, so arithmetic never
loses precision: ``1/3 + 1/3 + 1/3`` is exactly ``1``. That matters for a
teaching tool, because Gaussian elimination in floating point produces
answers like ``0.9999999999999998`` or ``-0.0`` that hide what is going on.
"""

from __future__ import annotations

from fractions import Fraction
from numbers import Rational
from typing import Iterable, Sequence

Number = int | Fraction


def to_fraction(value: object) -> Fraction:
    """Convert ints, Fractions, decimal floats and strings like '3/4' or '-1.5'."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("booleans are not matrix entries")
    if isinstance(value, Rational):  # int and friends
        return Fraction(value)
    if isinstance(value, float):
        # Go through repr so 0.1 becomes 1/10 rather than its binary expansion.
        return Fraction(repr(value))
    if isinstance(value, str):
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"not a number: {value!r}") from exc
    raise TypeError(f"cannot use {type(value).__name__} as a matrix entry")


class Matrix:
    """A rectangular, immutable matrix with exact rational entries."""

    __slots__ = ("_rows",)

    def __init__(self, rows: Iterable[Iterable[object]]):
        data = tuple(tuple(to_fraction(x) for x in row) for row in rows)
        if not data or not data[0]:
            raise ValueError("a matrix needs at least one row and one column")
        width = len(data[0])
        if any(len(row) != width for row in data):
            raise ValueError("all rows must have the same number of columns")
        self._rows: tuple[tuple[Fraction, ...], ...] = data

    # ---- constructors -------------------------------------------------
    @classmethod
    def identity(cls, n: int) -> "Matrix":
        return cls([[1 if i == j else 0 for j in range(n)] for i in range(n)])

    @classmethod
    def zeros(cls, rows: int, cols: int) -> "Matrix":
        return cls([[0] * cols for _ in range(rows)])

    # ---- shape and access ----------------------------------------------
    @property
    def rows(self) -> int:
        return len(self._rows)

    @property
    def cols(self) -> int:
        return len(self._rows[0])

    @property
    def shape(self) -> tuple[int, int]:
        return self.rows, self.cols

    @property
    def is_square(self) -> bool:
        return self.rows == self.cols

    def __getitem__(self, index: tuple[int, int]) -> Fraction:
        i, j = index
        return self._rows[i][j]

    def row(self, i: int) -> tuple[Fraction, ...]:
        return self._rows[i]

    def tolist(self) -> list[list[Fraction]]:
        """A mutable deep copy, used by the algorithms as a working buffer."""
        return [list(row) for row in self._rows]

    # ---- structural operations -----------------------------------------
    def transpose(self) -> "Matrix":
        return Matrix(zip(*self._rows))

    @property
    def T(self) -> "Matrix":  # noqa: N802 - conventional name
        return self.transpose()

    def augment(self, other: "Matrix") -> "Matrix":
        """Place ``other`` to the right of ``self``: [self | other]."""
        if self.rows != other.rows:
            raise ValueError("augment needs matrices with the same number of rows")
        return Matrix(a + b for a, b in zip(self._rows, other._rows))

    def submatrix(self, cols: slice) -> "Matrix":
        return Matrix(row[cols] for row in self._rows)

    def minor(self, i: int, j: int) -> "Matrix":
        """The matrix with row ``i`` and column ``j`` removed."""
        return Matrix(
            [x for c, x in enumerate(row) if c != j]
            for r, row in enumerate(self._rows)
            if r != i
        )

    # ---- arithmetic -----------------------------------------------------
    def __add__(self, other: "Matrix") -> "Matrix":
        self._check_same_shape(other, "+")
        return Matrix(
            (a + b for a, b in zip(r1, r2)) for r1, r2 in zip(self._rows, other._rows)
        )

    def __sub__(self, other: "Matrix") -> "Matrix":
        self._check_same_shape(other, "-")
        return Matrix(
            (a - b for a, b in zip(r1, r2)) for r1, r2 in zip(self._rows, other._rows)
        )

    def __neg__(self) -> "Matrix":
        return self * -1

    def __mul__(self, scalar: object) -> "Matrix":
        if isinstance(scalar, Matrix):
            return self @ scalar
        k = to_fraction(scalar)
        return Matrix((k * x for x in row) for row in self._rows)

    __rmul__ = __mul__

    def __matmul__(self, other: "Matrix") -> "Matrix":
        if self.cols != other.rows:
            raise ValueError(
                f"cannot multiply {self.rows}x{self.cols} by {other.rows}x{other.cols}"
            )
        other_cols = list(zip(*other._rows))
        return Matrix(
            (sum((a * b for a, b in zip(row, col)), Fraction(0)) for col in other_cols)
            for row in self._rows
        )

    def __pow__(self, n: int) -> "Matrix":
        """Integer power by repeated squaring; negative powers use the inverse."""
        if not self.is_square:
            raise ValueError("only square matrices can be raised to a power")
        if n < 0:
            from .operations import inverse  # local import avoids a cycle

            return inverse(self) ** -n
        result, base = Matrix.identity(self.rows), self
        while n:
            if n & 1:
                result = result @ base
            base = base @ base
            n >>= 1
        return result

    def trace(self) -> Fraction:
        if not self.is_square:
            raise ValueError("trace is only defined for square matrices")
        return sum((self._rows[i][i] for i in range(self.rows)), Fraction(0))

    # ---- comparison and display ----------------------------------------
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Matrix) and self._rows == other._rows

    def __hash__(self) -> int:
        return hash(self._rows)

    def __repr__(self) -> str:
        body = ", ".join("[" + ", ".join(fmt(x) for x in row) + "]" for row in self._rows)
        return f"Matrix([{body}])"

    def __str__(self) -> str:
        return render(self.tolist())

    def _check_same_shape(self, other: "Matrix", op: str) -> None:
        if self.shape != other.shape:
            raise ValueError(f"shape mismatch for {op}: {self.shape} vs {other.shape}")


def fmt(x: Fraction) -> str:
    """Format a Fraction as '3', '-1/2' etc."""
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def render(rows: Sequence[Sequence[Fraction]], divider: int | None = None) -> str:
    """Pretty-print rows as a bracketed, right-aligned grid.

    ``divider`` draws a vertical bar before that column, for augmented
    matrices like [A | b] or [A | I].
    """
    cells = [[fmt(x) for x in row] for row in rows]
    widths = [max(len(r[j]) for r in cells) for j in range(len(cells[0]))]
    n = len(cells)
    lines = []
    for i, row in enumerate(cells):
        parts = []
        for j, cell in enumerate(row):
            if divider is not None and j == divider:
                parts.append("|")
            parts.append(cell.rjust(widths[j]))
        left, right = ("[", "]") if n == 1 else (
            ("⎡", "⎤") if i == 0 else ("⎣", "⎦") if i == n - 1 else ("⎢", "⎥")
        )
        lines.append(f"{left} {' '.join(parts)} {right}")
    return "\n".join(lines)
