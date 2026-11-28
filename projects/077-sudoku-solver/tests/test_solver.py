import pytest

from sudoku import board as B
from sudoku import candidates, count_solutions, has_unique_solution, solve, solve_naive

EASY_SOLUTION = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"


@pytest.mark.parametrize("name", ["easy.txt", "hard.txt", "inkala.txt"])
def test_solves_and_respects_givens(load, name):
    p = load(name)
    res = solve(p)
    assert res.solved
    assert B.is_solved(res.solution)
    assert B.agrees_with(res.solution, p)


def test_known_solution(load):
    assert B.to_line(solve(load("easy.txt")).solution) == EASY_SOLUTION


def test_easy_needs_no_guessing(load):
    res = solve(load("easy.txt"))
    assert res.stats.guesses == 0 and res.stats.propagated > 0


def test_naive_matches_propagation(load):
    p = load("easy.txt")
    assert solve_naive(p).solution == solve(p).solution


def test_propagation_explores_far_fewer_nodes(load):
    p = load("inkala.txt")
    assert solve(p).stats.nodes * 50 < solve_naive(p).stats.nodes


def test_naive_node_limit(load):
    res = solve_naive(load("hard.txt"), max_nodes=1000)
    assert not res.solved and res.stats.nodes > 1000


def test_empty_board_is_solvable_with_many_solutions():
    empty = [0] * 81
    assert B.is_solved(solve(empty).solution)
    assert count_solutions(empty, limit=3) == 3


def test_conflicting_givens_unsolvable():
    p = [0] * 81
    p[0] = p[1] = 7
    assert not solve(p).solved
    assert not solve_naive(p).solved
    assert count_solutions(p) == 0


def test_valid_looking_but_unsolvable():
    # Row 0 has 1..8 in columns 0-7; column 8 already has a 9 lower down,
    # so the last cell of row 0 has no candidate. No direct conflicts.
    p = [0] * 81
    p[:8] = range(1, 9)
    p[9 * 4 + 8] = 9
    assert B.is_valid(p)
    assert not solve(p).solved
    assert candidates(p) == []


def test_uniqueness(load):
    assert has_unique_solution(load("hard.txt"))
    # Only the first row given: an enormous number of completions.
    p = [0] * 81
    p[:9] = range(1, 10)
    assert not has_unique_solution(p)
    # A complete grid with one cell blanked is trivially unique.
    full = B.parse(EASY_SOLUTION)
    full[40] = 0
    assert count_solutions(full, limit=5) == 1


def test_candidates_after_propagation(load):
    marks = candidates(load("hard.txt"))
    assert len(marks) == 81
    assert marks[0] == {4}  # a given stays fixed
    assert all(marks)  # nobody is empty in a solvable puzzle


def test_solve_does_not_mutate_input(load):
    p = load("easy.txt")
    before = p[:]
    solve(p)
    solve_naive(p)
    assert p == before
