"""Tic-tac-toe with an unbeatable minimax AI and a pygame UI."""

from .ai import AIPlayer, alphabeta, best_move, negamax
from .board import EMPTY, O, X, Board, IllegalMove
from .game import Game

__all__ = ["AIPlayer", "Board", "EMPTY", "Game", "IllegalMove", "O", "X",
           "alphabeta", "best_move", "negamax"]
__version__ = "1.0.0"
