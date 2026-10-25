import pytest

from tictactoe.board import EMPTY, O, X, Board, IllegalMove, other


def test_empty_board():
    b = Board()
    assert b.to_move == X
    assert b.legal_moves() == list(range(9))
    assert not b.is_terminal() and b.winner() is None


def test_play_alternates_and_is_immutable():
    b0 = Board()
    b1 = b0.play(4)
    assert b0.cells[4] == EMPTY  # original untouched
    assert b1.cells[4] == X and b1.to_move == O
    assert b1.play(0).cells[0] == O


@pytest.mark.parametrize("s,winner,line", [
    ("XXXOO....", X, (0, 1, 2)),
    ("OX.OX..X.", X, (1, 4, 7)),
    ("XXOXO.O..", O, (2, 4, 6)),
    ("X.OXO.X..", X, (0, 3, 6)),
])
def test_winner_detection(s, winner, line):
    b = Board.from_string(s)
    assert b.winner() == winner
    assert b.winning_line() == line
    assert b.is_terminal() and b.legal_moves() == []


def test_draw():
    b = Board.from_string("XOXXOOOXX")
    assert b.is_draw() and b.winner() is None


@pytest.mark.parametrize("bad", [-1, 9])
def test_off_board(bad):
    with pytest.raises(IllegalMove):
        Board().play(bad)


def test_occupied_and_finished():
    with pytest.raises(IllegalMove):
        Board().play(0).play(0)
    with pytest.raises(IllegalMove):
        Board.from_string("XXXOO....").play(8)


def test_rejects_unreachable_positions():
    with pytest.raises(ValueError):
        Board.from_string("OO.......")
    with pytest.raises(ValueError):
        Board.from_string("XX.......")
    with pytest.raises(ValueError):
        Board.from_string("XX?......")


def test_hashable_and_str():
    assert hash(Board()) == hash(Board())
    assert "5" in str(Board()) and "X" in str(Board().play(4))


def test_other():
    assert other(X) == O and other(O) == X
    with pytest.raises(ValueError):
        other(EMPTY)
