"""Maze solvers: breadth-first search and A*.

In a perfect maze the path between two cells is unique, so both solvers return
the same path; they differ in how many cells they *explore* to find it, which
the result reports so the two can be compared.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass

from .maze import Cell, Maze


@dataclass
class Solution:
    path: list[Cell]       # start..goal inclusive; empty if unreachable
    explored: int          # number of cells popped from the frontier

    @property
    def length(self) -> int:
        """Number of moves (edges) along the path."""
        return max(len(self.path) - 1, 0)


def _reconstruct(came_from: dict[Cell, Cell | None], goal: Cell) -> list[Cell]:
    if goal not in came_from:
        return []
    path = []
    cur: Cell | None = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path


def bfs(maze: Maze, start: Cell | None = None, goal: Cell | None = None) -> Solution:
    """Unweighted shortest path by breadth-first search. O(V + E)."""
    start = maze.start if start is None else start
    goal = maze.end if goal is None else goal
    came_from: dict[Cell, Cell | None] = {start: None}
    queue = deque([start])
    explored = 0
    while queue:
        cell = queue.popleft()
        explored += 1
        if cell == goal:
            break
        for n in maze.neighbors(cell):
            if n not in came_from:
                came_from[n] = cell
                queue.append(n)
    return Solution(_reconstruct(came_from, goal), explored)


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(maze: Maze, start: Cell | None = None, goal: Cell | None = None) -> Solution:
    """A* with the Manhattan heuristic (admissible on a 4-connected grid)."""
    start = maze.start if start is None else start
    goal = maze.end if goal is None else goal
    came_from: dict[Cell, Cell | None] = {start: None}
    g = {start: 0}
    # Heap entries: (f = g + h, tie-breaker counter, cell)
    counter = 0
    frontier = [(manhattan(start, goal), counter, start)]
    closed: set[Cell] = set()
    while frontier:
        _, _, cell = heapq.heappop(frontier)
        if cell in closed:
            continue  # stale entry left behind by a later, cheaper push
        closed.add(cell)
        if cell == goal:
            break
        for n in maze.neighbors(cell):
            ng = g[cell] + 1
            if ng < g.get(n, float("inf")):
                g[n] = ng
                came_from[n] = cell
                counter += 1
                heapq.heappush(frontier, (ng + manhattan(n, goal), counter, n))
    return Solution(_reconstruct(came_from, goal), len(closed))
