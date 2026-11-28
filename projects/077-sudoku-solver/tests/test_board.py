import pytest

from sudoku import board as B

EASY = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"


def test_geometry():
    assert len(B.UNITS) == 27
    assert all(len(u) == 9 for u in B.UNITS)
    assert all(len(p) == 20 for p in B.PEERS)
    assert all(len(cu) == 3 for cu in B.CELL_UNITS)
    # cell 0's box is the top-left 3x3
    assert B.BOXES[0] == [0, 1, 2, 9, 10, 11, 18, 19, 20]
    assert 80 not in B.PEERS[0] and 10 in B.PEERS[0]


def test_parse_line_and_grid_agree(load):
    assert load("easy.txt") == load("grid.txt")
    assert B.to_line(load("easy.txt")) == EASY


def test_parse_accepts_zero_and_underscore():
    assert B.parse(EASY.replace(".", "0")) == B.parse(EASY.replace(".", "_"))


@pytest.mark.parametrize("text", [EASY[:-1], EASY + "1", EASY[:-1] + "x"])
def test_parse_errors(text):
    with pytest.raises(B.ParseError):
        B.parse(text)


def test_roundtrip_grid(load):
    p = load("easy.txt")
    assert B.parse(B.to_grid(p)) == p


def test_conflicts_detected():
    p = B.parse(EASY)
    p[1] = 5  # second 5 in row 0 (and box 0)
    assert not B.is_valid(p)
    assert (0, 1) in B.conflicts(p)


def test_is_solved_rejects_partial(load):
    assert not B.is_solved(load("easy.txt"))
