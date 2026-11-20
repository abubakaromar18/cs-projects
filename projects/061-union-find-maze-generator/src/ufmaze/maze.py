"""Maze representation and randomized-Kruskal generation.

A rectangular maze is modelled as a graph: each cell is a vertex and each pair
of orthogonally adjacent cells is an edge (a wall that may be knocked down).
A *perfect* maze -- exactly one path between any two cells -- is precisely a
spanning tree of that grid graph.

Randomized Kruskal builds such a tree: shuffle every interior wall, then walk
the list and remove a wall whenever the two cells on either side are not yet
connected. Union-find answers "already connected?" in near-constant time.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterator

from .unionfind import UnionFind

Cell = tuple[int, int]  # (row, col)


@dataclass
class Maze:
    rows: int
    cols: int
    #: Set of open passages; each passage is a frozenset of two adjacent cells.
    passages: set[frozenset[Cell]] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.rows < 1 or self.cols < 1:
            raise ValueError("maze must be at least 1x1")

    # -- geometry ---------------------------------------------------------
    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def index(self, cell: Cell) -> int:
        """Flatten (row, col) to an integer id for the union-find."""
        return cell[0] * self.cols + cell[1]

    def cells(self) -> Iterator[Cell]:
        for r in range(self.rows):
            for c in range(self.cols):
                yield (r, c)

    def grid_neighbors(self, cell: Cell) -> Iterator[Cell]:
        """All in-bounds orthogonal neighbours, ignoring walls."""
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = (r + dr, c + dc)
            if self.in_bounds(n):
                yield n

    def walls(self) -> list[tuple[Cell, Cell]]:
        """Every interior wall, i.e. every edge of the full grid graph."""
        edges = []
        for r, c in self.cells():
            if c + 1 < self.cols:
                edges.append(((r, c), (r, c + 1)))
            if r + 1 < self.rows:
                edges.append(((r, c), (r + 1, c)))
        return edges

    # -- passages ---------------------------------------------------------
    def carve(self, a: Cell, b: Cell) -> None:
        if b not in set(self.grid_neighbors(a)):
            raise ValueError(f"{a} and {b} are not adjacent")
        self.passages.add(frozenset((a, b)))

    def is_open(self, a: Cell, b: Cell) -> bool:
        return frozenset((a, b)) in self.passages

    def neighbors(self, cell: Cell) -> Iterator[Cell]:
        """Neighbours reachable through an open passage."""
        for n in self.grid_neighbors(cell):
            if self.is_open(cell, n):
                yield n

    @property
    def start(self) -> Cell:
        return (0, 0)

    @property
    def end(self) -> Cell:
        return (self.rows - 1, self.cols - 1)


def generate(rows: int, cols: int, seed: int | None = None,
             on_step=None) -> Maze:
    """Generate a perfect maze with randomized Kruskal's algorithm.

    ``seed`` makes output reproducible. ``on_step(maze, a, b)`` is called after
    each wall removal, which is handy for animation or teaching.
    """
    rng = random.Random(seed)
    maze = Maze(rows, cols)
    walls = maze.walls()
    rng.shuffle(walls)  # random edge weights == random edge order

    uf = UnionFind(rows * cols)
    target = rows * cols - 1  # a spanning tree on V vertices has V-1 edges
    for a, b in walls:
        if uf.union(maze.index(a), maze.index(b)):
            maze.carve(a, b)
            if on_step is not None:
                on_step(maze, a, b)
            if len(maze.passages) == target:
                break  # early exit: tree is complete
    return maze


def is_perfect(maze: Maze) -> bool:
    """True iff the passages form a spanning tree (connected and acyclic)."""
    n = maze.rows * maze.cols
    if len(maze.passages) != n - 1:
        return False
    uf = UnionFind(n)
    for p in maze.passages:
        a, b = tuple(p)
        if not uf.union(maze.index(a), maze.index(b)):
            return False  # cycle
    return uf.components == 1
