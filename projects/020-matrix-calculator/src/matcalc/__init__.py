"""matcalc: an exact-arithmetic matrix calculator that shows its work."""

from .matrix import Matrix
from .operations import (
    SingularMatrixError,
    determinant,
    determinant_cofactor,
    inverse,
    inverse_with_steps,
    rank,
    rref,
    solve,
)
from .parser import parse_matrix

__version__ = "1.0.0"

__all__ = [
    "Matrix",
    "SingularMatrixError",
    "determinant",
    "determinant_cofactor",
    "inverse",
    "inverse_with_steps",
    "parse_matrix",
    "rank",
    "rref",
    "solve",
]
