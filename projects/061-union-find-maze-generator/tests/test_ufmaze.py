import random

import pytest

from ufmaze import render, solver
from ufmaze.cli import main
from ufmaze.maze import Maze, generate, is_perfect
from ufmaze.unionfind import UnionFind


# ---------------------------------------------------------------- union-find
def test_union_find_basic():
    uf = UnionFind(6)
    assert uf.components == 6
    assert uf.union(0, 1)
    assert uf.union(2, 3)
    assert not uf.union(1, 0)  # already joined
    assert uf.connected(0, 1) and not uf.connected(1, 2)
    assert uf.union(1, 3)
    assert uf.connected(0, 2)
    assert uf.components == 3
    assert uf.size_of(3) == 4


def test_union_find_matches_naive_model():
    rng = random.Random(1)
    n = 200
    uf = UnionFind(n)
    label = list(range(n))  # naive: relabel whole group on merge
    for _ in range(1000):
        a, b = rng.randrange(n), rng.randrange(n)
        merged = uf.union(a, b)
        assert merged == (label[a] != label[b])
        if merged:
            old, new = label[b], label[a]
            label = [new if x == old else x for x in label]
    for _ in range(500):
        a, b = rng.randrange(n), rng.randrange(n)
        assert uf.connected(a, b) == (label[a] == label[b])
    assert uf.components == len(set(label))


def test_union_find_long_chain_no_recursion_error():
    n = 100_000
    uf = UnionFind(n)
    for i in range(n - 1):
        uf.union(i, i + 1)
    assert uf.connected(0, n - 1)
    assert uf.components == 1


def test_union_find_rejects_negative():
    with pytest.raises(ValueError):
        UnionFind(-1)


# ---------------------------------------------------------------- generation
@pytest.mark.parametrize("rows,cols", [(1, 1), (1, 7), (7, 1), (5, 5), (12, 30)])
def test_generated_maze_is_perfect(rows, cols):
    for seed in range(5):
        m = generate(rows, cols, seed=seed)
        assert len(m.passages) == rows * cols - 1
        assert is_perfect(m)


def test_seed_is_reproducible():
    assert generate(15, 15, seed=42).passages == generate(15, 15, seed=42).passages
    assert generate(15, 15, seed=1).passages != generate(15, 15, seed=2).passages


def test_is_perfect_detects_cycle_and_disconnection():
    m = Maze(2, 2)
    m.carve((0, 0), (0, 1))
    m.carve((0, 1), (1, 1))
    assert not is_perfect(m)           # (1,0) disconnected
    m.carve((1, 1), (1, 0))
    assert is_perfect(m)
    m.carve((1, 0), (0, 0))
    assert not is_perfect(m)           # 4 edges on 4 cells -> cycle


def test_carve_rejects_non_adjacent():
    with pytest.raises(ValueError):
        Maze(3, 3).carve((0, 0), (2, 2))


def test_on_step_called_once_per_passage():
    calls = []
    generate(6, 6, seed=0, on_step=lambda m, a, b: calls.append((a, b)))
    assert len(calls) == 35


# ---------------------------------------------------------------- solving
def _valid_path(m, path):
    return all(m.is_open(a, b) for a, b in zip(path, path[1:]))


@pytest.mark.parametrize("seed", range(10))
def test_bfs_and_astar_agree(seed):
    m = generate(20, 25, seed=seed)
    b, a = solver.bfs(m), solver.astar(m)
    assert b.path[0] == m.start and b.path[-1] == m.end
    assert _valid_path(m, b.path)
    assert b.path == a.path  # unique path in a perfect maze
    assert a.explored <= m.rows * m.cols


def test_path_on_open_grid_is_manhattan():
    # A maze that is a straight corridor: shortest path must be its length.
    m = Maze(1, 10)
    for c in range(9):
        m.carve((0, c), (0, c + 1))
    assert solver.bfs(m).length == 9
    assert solver.astar(m).length == 9


def test_unreachable_goal_returns_empty_path():
    m = Maze(2, 2)  # no passages at all
    assert solver.bfs(m).path == []
    assert solver.astar(m).path == []
    assert solver.bfs(m).length == 0


def test_single_cell():
    m = generate(1, 1, seed=0)
    assert solver.bfs(m).path == [(0, 0)]


# ---------------------------------------------------------------- rendering & CLI
def test_ascii_dimensions_and_markers():
    m = generate(4, 6, seed=3)
    art = render.to_ascii(m, solver.bfs(m).path)
    lines = art.splitlines()
    assert len(lines) == 2 * 4 + 1
    assert all(len(line) == 4 * 6 + 1 for line in lines)
    assert "S" in art and "E" in art


def test_ascii_wall_count_matches_passages():
    m = generate(5, 5, seed=9)
    art = render.to_ascii(m)
    # Interior walls = all grid edges minus passages.
    interior = len(m.walls()) - len(m.passages)
    body_rows = art.splitlines()[1::2]
    floor_rows = art.splitlines()[2:-1:2]
    vertical = sum(row[1:-1].count("|") for row in body_rows)
    horizontal = sum(row.count("---") for row in floor_rows)
    assert vertical + horizontal == interior


def test_svg_is_well_formed():
    import xml.etree.ElementTree as ET
    m = generate(5, 8, seed=0)
    root = ET.fromstring(render.to_svg(m, solver.bfs(m).path))
    assert root.tag.endswith("svg")


def test_cli(tmp_path, capsys):
    out = tmp_path / "m.svg"
    assert main(["-r", "5", "-c", "5", "-s", "1", "--solve", "astar",
                 "--svg", str(out), "--stats"]) == 0
    text = capsys.readouterr().out
    assert "astar: path length" in text
    assert out.read_text().startswith("<svg")


def test_cli_rejects_bad_size(capsys):
    assert main(["-r", "0"]) == 2
