"""Board representation, geometry, parsing and formatting.

A board is stored as a flat tuple/list of 81 ints, row-major, where 0 means
"empty". Cell ``i`` sits at row ``i // 9`` and column ``i % 9``.

The geometry of Sudoku never changes, so we precompute it once:

* ``UNITS``  - the 27 groups (9 rows, 9 columns, 9 boxes) that must each
  contain the digits 1-9 exactly once.
* ``CELL_UNITS[i]`` - the 3 units that cell ``i`` belongs to.
* ``PEERS[i]`` - the 20 other cells that share a unit with ``i``. A digit
  placed in ``i`` is forbidden in all of its peers.
"""

from __future__ import annotations

from typing import Iterable, Sequence

SIZE = 9
BOX = 3
CELLS = SIZE * SIZE
DIGITS = range(1, SIZE + 1)

ROWS = [[r * SIZE + c for c in range(SIZE)] for r in range(SIZE)]
COLS = [[r * SIZE + c for r in range(SIZE)] for c in range(SIZE)]
BOXES = [
    [(br + r) * SIZE + (bc + c) for r in range(BOX) for c in range(BOX)]
    for br in range(0, SIZE, BOX)
    for bc in range(0, SIZE, BOX)
]
UNITS: list[list[int]] = ROWS + COLS + BOXES
CELL_UNITS: list[list[list[int]]] = [[u for u in UNITS if i in u] for i in range(CELLS)]
PEERS: list[frozenset[int]] = [
    frozenset(j for u in CELL_UNITS[i] for j in u if j != i) for i in range(CELLS)
]

_EMPTY_CHARS = set(".0_")
_IGNORED_CHARS = set("|-+ \t\r\n")


class ParseError(ValueError):
    """Raised when text cannot be turned into a 9x9 board."""


def parse(text: str) -> list[int]:
    """Parse a puzzle from a single 81-char line or a decorated grid.

    Lines starting with ``#`` are comments. Digits 1-9 are givens; ``.``,
    ``0`` and ``_`` are blanks; grid decoration (``| - +`` and whitespace)
    is ignored. Anything else is an error.
    """
    cells: list[int] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for ch in line:
            if ch in _IGNORED_CHARS:
                continue
            if ch in _EMPTY_CHARS:
                cells.append(0)
            elif ch.isdigit():
                cells.append(int(ch))
            else:
                raise ParseError(f"unexpected character {ch!r}")
    if len(cells) != CELLS:
        raise ParseError(f"expected {CELLS} cells, found {len(cells)}")
    return cells


def to_line(board: Sequence[int]) -> str:
    """Compact single-line form, e.g. ``53..7....6..``."""
    return "".join(str(v) if v else "." for v in board)


def to_grid(board: Sequence[int]) -> str:
    """Human-friendly grid with box separators."""
    out: list[str] = []
    for r in range(SIZE):
        if r and r % BOX == 0:
            out.append("------+-------+------")
        row = board[r * SIZE : (r + 1) * SIZE]
        chunks = [
            " ".join(str(v) if v else "." for v in row[c : c + BOX])
            for c in range(0, SIZE, BOX)
        ]
        out.append(" | ".join(chunks))
    return "\n".join(out)


def conflicts(board: Sequence[int]) -> list[tuple[int, int]]:
    """Return pairs of cells holding the same digit within one unit."""
    found: list[tuple[int, int]] = []
    for unit in UNITS:
        seen: dict[int, int] = {}
        for i in unit:
            v = board[i]
            if v:
                if v in seen:
                    found.append((seen[v], i))
                else:
                    seen[v] = i
    return found


def is_valid(board: Sequence[int]) -> bool:
    """True if the givens don't contradict each other (may still be unsolvable)."""
    return len(board) == CELLS and all(0 <= v <= 9 for v in board) and not conflicts(board)


def is_solved(board: Sequence[int]) -> bool:
    """True if every cell is filled and every unit holds 1-9."""
    full = set(DIGITS)
    return len(board) == CELLS and all(
        {board[i] for i in unit} == full for unit in UNITS
    )


def agrees_with(solution: Sequence[int], puzzle: Iterable[int]) -> bool:
    """True if ``solution`` keeps every given of ``puzzle``."""
    return all(p == 0 or p == s for p, s in zip(puzzle, solution))
