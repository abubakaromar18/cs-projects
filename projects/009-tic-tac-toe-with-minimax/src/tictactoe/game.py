"""UI-independent game controller shared by the pygame and terminal front ends.

Keeping turn order, scoring and undo here means both UIs stay thin and the
rules can be unit-tested without opening a window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .ai import AIPlayer
from .board import O, X, Board, other


@dataclass
class Score:
    human: int = 0
    ai: int = 0
    draws: int = 0


@dataclass
class Game:
    human: str = X
    ai: AIPlayer = field(default_factory=AIPlayer)
    board: Board = field(default_factory=Board)
    history: list[Board] = field(default_factory=list)
    score: Score = field(default_factory=Score)
    _recorded: bool = False

    def __post_init__(self) -> None:
        if self.human not in (X, O):
            raise ValueError("human must play 'X' or 'O'")

    @property
    def ai_mark(self) -> str:
        return other(self.human)

    @property
    def over(self) -> bool:
        return self.board.is_terminal()

    def is_human_turn(self) -> bool:
        return not self.over and self.board.to_move == self.human

    def is_ai_turn(self) -> bool:
        return not self.over and self.board.to_move == self.ai_mark

    def _apply(self, index: int) -> None:
        self.history.append(self.board)
        self.board = self.board.play(index)
        self._record_result()

    def human_move(self, index: int) -> None:
        """Play the human's move. Raises IllegalMove / RuntimeError if invalid."""
        if not self.is_human_turn():
            raise RuntimeError("it is not the human's turn")
        self._apply(index)

    def ai_move(self) -> int:
        """Let the AI pick and play a move; returns the chosen cell."""
        if not self.is_ai_turn():
            raise RuntimeError("it is not the AI's turn")
        move = self.ai.choose(self.board)
        self._apply(move)
        return move

    def undo(self) -> None:
        """Take back the last human move (and the AI reply that followed it)."""
        if self._recorded:
            self._unrecord_result()
        # Pop until it is the human's turn again with at least one move undone.
        popped = False
        while self.history and (not popped or self.board.to_move != self.human):
            self.board = self.history.pop()
            popped = True

    def new_round(self, swap_sides: bool = False) -> None:
        if swap_sides:
            self.human = other(self.human)
        self.board = Board()
        self.history.clear()
        self._recorded = False

    def result_text(self) -> Optional[str]:
        if not self.over:
            return None
        w = self.board.winner()
        if w is None:
            return "Draw!"
        return "You win!" if w == self.human else "AI wins!"

    # Results are tallied exactly once per finished game, and reversed on undo.
    def _record_result(self) -> None:
        if not self.over or self._recorded:
            return
        w = self.board.winner()
        if w is None:
            self.score.draws += 1
        elif w == self.human:
            self.score.human += 1
        else:
            self.score.ai += 1
        self._recorded = True

    def _unrecord_result(self) -> None:
        w = self.board.winner()
        if w is None:
            self.score.draws -= 1
        elif w == self.human:
            self.score.human -= 1
        else:
            self.score.ai -= 1
        self._recorded = False
