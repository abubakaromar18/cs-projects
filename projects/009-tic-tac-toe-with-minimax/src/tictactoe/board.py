"""Immutable tic-tac-toe board.

The board is stored as a tuple of nine cells, indexed row-major:

     0 | 1 | 2
    ---+---+---
     3 | 4 | 5
    ---+---+---
     6 | 7 | 8

Keeping the board immutable (every move returns a *new* Board) makes it
hashable, which lets the AI memoise positions in a transposition table,
and removes a whole class of "forgot to undo the move" bugs from search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

X = "X"
O = "O"
EMPTY = " "

# Every way to get three in a row: 3 rows, 3 columns, 2 diagonals.
WIN_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)


def other(player: str) -> str:
    """Return the opponent of ``player``."""
    if player not in (X, O):
        raise ValueError(f"not a player: {player!r}")
    return O if player == X else X


class IllegalMove(ValueError):
    """Raised when a move targets an occupied cell, is off the board,
    or is played after the game has ended."""


@dataclass(frozen=True)
class Board:
    cells: tuple[str, ...] = (EMPTY,) * 9

    def __post_init__(self) -> None:
        if len(self.cells) != 9:
            raise ValueError("a board has exactly 9 cells")
        if any(c not in (X, O, EMPTY) for c in self.cells):
            raise ValueError("cells must be 'X', 'O' or ' '")
        xs, os_ = self.cells.count(X), self.cells.count(O)
        # X always moves first, so X has either the same count or one more.
        if not (xs == os_ or xs == os_ + 1):
            raise ValueError("unreachable position: X moves first and players alternate")

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_string(cls, s: str) -> "Board":
        """Build a board from a 9-character string; '.', '_' or ' ' mean empty.

        >>> Board.from_string("XO.......").cells[:3]
        ('X', 'O', ' ')
        """
        s = s.replace("\n", "").replace("|", "")
        if len(s) != 9:
            raise ValueError("expected 9 cells")
        mapping = {".": EMPTY, "_": EMPTY, " ": EMPTY, "x": X, "o": O, "X": X, "O": O}
        try:
            return cls(tuple(mapping[ch] for ch in s))
        except KeyError as exc:
            raise ValueError(f"bad cell character: {exc.args[0]!r}") from None

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    @property
    def to_move(self) -> str:
        """Whose turn it is. X moves first."""
        return X if self.cells.count(X) == self.cells.count(O) else O

    def legal_moves(self) -> list[int]:
        """Indices of empty cells, or [] if the game is over."""
        if self.is_terminal():
            return []
        return [i for i, c in enumerate(self.cells) if c == EMPTY]

    def winner(self) -> Optional[str]:
        """'X' or 'O' if someone has three in a row, else None."""
        line = self.winning_line()
        return self.cells[line[0]] if line else None

    def winning_line(self) -> Optional[tuple[int, int, int]]:
        """The completed line (for highlighting in the UI), if any."""
        for a, b, c in WIN_LINES:
            if self.cells[a] != EMPTY and self.cells[a] == self.cells[b] == self.cells[c]:
                return (a, b, c)
        return None

    def is_full(self) -> bool:
        return EMPTY not in self.cells

    def is_terminal(self) -> bool:
        return self.winner() is not None or self.is_full()

    def is_draw(self) -> bool:
        return self.is_full() and self.winner() is None

    # ------------------------------------------------------------------ #
    # Moves
    # ------------------------------------------------------------------ #
    def play(self, index: int) -> "Board":
        """Return a new board with the current player's mark at ``index``."""
        if not 0 <= index < 9:
            raise IllegalMove(f"cell {index} is off the board")
        if self.is_terminal():
            raise IllegalMove("the game is already over")
        if self.cells[index] != EMPTY:
            raise IllegalMove(f"cell {index} is already taken")
        cells = list(self.cells)
        cells[index] = self.to_move
        return Board(tuple(cells))

    def children(self) -> Iterator[tuple[int, "Board"]]:
        """Yield (move, resulting board) for each legal move."""
        for m in self.legal_moves():
            yield m, self.play(m)

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        rows = []
        for r in range(3):
            row = []
            for c in range(3):
                i = r * 3 + c
                # Show the cell number for empty squares so the CLI is self-explaining.
                row.append(self.cells[i] if self.cells[i] != EMPTY else str(i + 1))
            rows.append(" " + " | ".join(row))
        return "\n---+---+---\n".join(rows)
