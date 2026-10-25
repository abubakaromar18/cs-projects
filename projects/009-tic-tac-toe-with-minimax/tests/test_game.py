import random

import pytest

from tictactoe.ai import AIPlayer
from tictactoe.board import O, X, Board
from tictactoe.game import Game


def test_turns_and_ai_reply():
    g = Game(human=X)
    assert g.is_human_turn()
    g.human_move(0)
    assert g.is_ai_turn()
    move = g.ai_move()
    assert g.board.cells[move] == O and g.is_human_turn()
    with pytest.raises(RuntimeError):
        g.ai_move()


def test_human_as_o_ai_opens():
    g = Game(human=O)
    assert g.is_ai_turn()
    assert g.ai_move() == 4  # centre is the tie-break favourite
    with pytest.raises(RuntimeError):
        Game(human=O).human_move(0)


def test_undo_removes_human_and_ai_moves():
    g = Game()
    g.human_move(0)
    g.ai_move()
    g.undo()
    assert g.board == Board() and g.history == []


def test_scoring_and_undo_reverses_it():
    g = Game(human=X, board=Board.from_string("XX.OO...."))
    g.human_move(2)
    assert g.over and g.result_text() == "You win!"
    assert g.score.human == 1
    g.undo()
    assert g.score.human == 0 and not g.over


def test_draw_and_ai_win_are_scored():
    g = Game(human=X, ai=AIPlayer("hard"))
    # Human plays randomly against perfect AI for many rounds: never wins.
    rng = random.Random(3)
    for _ in range(20):
        while not g.over:
            if g.is_human_turn():
                g.human_move(rng.choice(g.board.legal_moves()))
            else:
                g.ai_move()
        g.new_round()
    assert g.score.human == 0
    assert g.score.ai + g.score.draws == 20


def test_new_round_swaps_sides():
    g = Game(human=X)
    g.new_round(swap_sides=True)
    assert g.human == O and g.ai_mark == X and g.board == Board()


def test_invalid_human_mark():
    with pytest.raises(ValueError):
        Game(human="Z")
