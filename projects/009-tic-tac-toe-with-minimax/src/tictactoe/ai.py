"""Game-tree search for tic-tac-toe.

Two searches are provided:

* :func:`negamax` -- plain minimax in its *negamax* form, memoised with a
  transposition table (``functools.lru_cache``). Because tic-tac-toe has only
  5,478 reachable positions, caching makes the full solve instant.

* :func:`alphabeta` -- the same search with alpha-beta pruning and *no* cache,
  instrumented to count visited nodes so you can see how much pruning saves
  compared to :func:`count_minimax_nodes` (the raw, unpruned tree).

Scores are always from the point of view of the player *to move*:

* positive  -> the side to move can force a win
* zero      -> best play leads to a draw
* negative  -> the side to move loses against best play

Wins are scored ``1 + empty_cells`` so a *faster* win scores higher and a
*slower* loss scores higher (less negative). This makes the AI finish games
promptly instead of toying with its opponent, and stall when lost.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from .board import EMPTY, Board

INF = 10**9

# Preferred order when several moves are equally good: centre, corners, edges.
# Searching good moves first also makes alpha-beta prune more.
MOVE_ORDER = (4, 0, 2, 6, 8, 1, 3, 5, 7)


def _ordered(moves: list[int]) -> list[int]:
    return sorted(moves, key=MOVE_ORDER.index)


def terminal_score(board: Board) -> Optional[int]:
    """Score of a finished game from the side-to-move's view, else None."""
    if board.winner() is not None:
        # The player who just moved won, so the side to move has lost.
        return -(1 + board.cells.count(EMPTY))
    if board.is_full():
        return 0
    return None


# ---------------------------------------------------------------------- #
# Memoised negamax
# ---------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def negamax(board: Board) -> int:
    """Exact game-theoretic value of ``board`` for the side to move."""
    score = terminal_score(board)
    if score is not None:
        return score
    # Negamax identity: max(a, b) == -min(-a, -b), so one function serves both players.
    return max(-negamax(child) for _, child in board.children())


def move_scores(board: Board) -> dict[int, int]:
    """Value of every legal move for the side to move."""
    return {m: -negamax(child) for m, child in board.children()}


# ---------------------------------------------------------------------- #
# Alpha-beta (uncached, instrumented)
# ---------------------------------------------------------------------- #
@dataclass
class SearchStats:
    nodes: int = 0
    cutoffs: int = 0


def alphabeta(board: Board, alpha: int = -INF, beta: int = INF,
              stats: Optional[SearchStats] = None) -> int:
    """Negamax with alpha-beta pruning.

    ``alpha`` is the best score the side to move is already guaranteed;
    ``beta`` is the best the *opponent* is guaranteed. Once a move scores
    ``>= beta`` the opponent will never allow this position, so the remaining
    siblings can be skipped (a "beta cutoff").
    """
    if stats is not None:
        stats.nodes += 1
    score = terminal_score(board)
    if score is not None:
        return score
    best = -INF
    for move in _ordered(board.legal_moves()):
        value = -alphabeta(board.play(move), -beta, -alpha, stats)
        best = max(best, value)
        alpha = max(alpha, value)
        if alpha >= beta:
            if stats is not None:
                stats.cutoffs += 1
            break
    return best


def count_minimax_nodes(board: Board) -> int:
    """Size of the full, unpruned game tree below ``board`` (inclusive)."""
    if board.is_terminal():
        return 1
    return 1 + sum(count_minimax_nodes(child) for _, child in board.children())


# ---------------------------------------------------------------------- #
# Players
# ---------------------------------------------------------------------- #
DIFFICULTIES = ("easy", "medium", "hard")


@dataclass
class AIPlayer:
    """A computer opponent.

    * ``hard``   -- perfect play; can never be beaten.
    * ``medium`` -- plays perfectly 70% of the time, otherwise randomly.
    * ``easy``   -- random legal moves, but takes an immediate win if offered.
    """

    difficulty: str = "hard"
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {DIFFICULTIES}")

    def choose(self, board: Board) -> int:
        moves = board.legal_moves()
        if not moves:
            raise ValueError("no legal moves: the game is over")
        if self.difficulty == "easy":
            for m in moves:
                if board.play(m).winner():
                    return m
            return self.rng.choice(moves)
        if self.difficulty == "medium" and self.rng.random() < 0.3:
            return self.rng.choice(moves)
        return best_move(board)


def best_move(board: Board) -> int:
    """A perfect move; ties broken by centre > corners > edges for determinism."""
    scores = move_scores(board)
    if not scores:
        raise ValueError("no legal moves: the game is over")
    top = max(scores.values())
    return next(m for m in MOVE_ORDER if scores.get(m) == top)
