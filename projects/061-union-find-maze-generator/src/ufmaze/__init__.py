"""Union-find maze generator: randomized Kruskal mazes, BFS/A* solvers, ASCII/SVG output."""

from .maze import Maze, generate, is_perfect
from .unionfind import UnionFind

__all__ = ["Maze", "UnionFind", "generate", "is_perfect"]
__version__ = "1.0.0"
