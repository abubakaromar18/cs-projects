"""Sudoku solver: backtracking with constraint propagation."""

from .board import ParseError, is_solved, is_valid, parse, to_grid, to_line
from .generator import generate
from .solver import Result, Stats, candidates, count_solutions, has_unique_solution, solve, solve_naive

__all__ = [
    "ParseError", "parse", "to_grid", "to_line", "is_valid", "is_solved",
    "solve", "solve_naive", "count_solutions", "has_unique_solution", "candidates",
    "generate", "Result", "Stats",
]
__version__ = "1.0.0"
