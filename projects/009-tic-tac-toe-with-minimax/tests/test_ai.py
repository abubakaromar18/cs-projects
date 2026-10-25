import random

import pytest

from tictactoe.ai import (AIPlayer, SearchStats, alphabeta, best_move,
                          count_minimax_nodes, move_scores, negamax)
from tictactoe.board import O, X, Board


def all_positions():
    """Every reachable, non-terminal position (DFS over the game tree)."""
    seen, stack = set(), [Board()]
    while stack:
        b = stack.pop()
        if b in seen:
            continue
        seen.add(b)
        stack.extend(child for _, child in b.children())
    return seen


def test_empty_board_is_a_draw():
    assert negamax(Board()) == 0


def test_reachable_position_count():
    # A well-known figure: 5,478 legal positions are reachable from the start.
    assert len(all_positions()) == 5478


def test_alphabeta_agrees_with_minimax_everywhere():
    for b in all_positions():
        assert alphabeta(b) == negamax(b), str(b)


def test_alphabeta_prunes():
    s = SearchStats()
    alphabeta(Board(), stats=s)
    assert s.nodes < count_minimax_nodes(Board()) / 10
    assert s.cutoffs > 0


def test_full_tree_size():
    # Known result: 549,946 nodes in the full tic-tac-toe game tree.
    assert count_minimax_nodes(Board()) == 549946


def test_takes_immediate_win():
    b = Board.from_string("XX.OO....")
    assert best_move(b) == 2


def test_blocks_immediate_loss():
    b = Board.from_string("OO.X.X..X")   # X=3, O=2 -> O to move
    assert b.to_move == O
    assert best_move(b) == 2           # O wins at 2
    b2 = Board.from_string("OO.XX....")  # X to move, must win at 5
    assert best_move(b2) == 5
    b3 = Board.from_string("OO.X....X")  # X to move, must block at 2
    assert best_move(b3) == 2


def test_prefers_faster_win():
    # X can win now at 2; other moves also win but later. Fastest must score highest.
    b = Board.from_string("XX.O.O...")
    scores = move_scores(b)
    assert best_move(b) == 2
    assert scores[2] == max(scores.values())


def _ai_never_loses(ai_mark):
    """Explore *every* opponent reply against the hard AI; it must never lose."""
    ai = AIPlayer("hard")
    stack = [Board()]
    games = 0
    while stack:
        b = stack.pop()
        if b.is_terminal():
            assert b.winner() != (O if ai_mark == X else X), f"AI lost:\n{b}"
            games += 1
        elif b.to_move == ai_mark:
            stack.append(b.play(ai.choose(b)))
        else:
            stack.extend(child for _, child in b.children())
    return games


@pytest.mark.parametrize("mark", [X, O])
def test_hard_ai_is_unbeatable(mark):
    assert _ai_never_loses(mark) > 0


def test_difficulties_and_validation():
    rng = random.Random(0)
    b = Board.from_string("XX.OO....")
    assert AIPlayer("easy", rng).choose(b) == 2  # easy still grabs a win
    for level in ("easy", "medium", "hard"):
        assert AIPlayer(level, rng).choose(Board()) in range(9)
    with pytest.raises(ValueError):
        AIPlayer("impossible")
    with pytest.raises(ValueError):
        AIPlayer().choose(Board.from_string("XXXOO...."))


def test_easy_ai_can_be_beaten():
    # Against random play, a perfect player should win at least sometimes.
    rng = random.Random(1)
    wins = 0
    for _ in range(50):
        b = Board()
        easy = AIPlayer("easy", rng)
        while not b.is_terminal():
            b = b.play(best_move(b) if b.to_move == X else easy.choose(b))
        wins += b.winner() == X
    assert wins > 10
