# 061 · Union-Find Maze Generator

Generates **perfect mazes** (exactly one path between any two cells) with
**randomized Kruskal's algorithm** backed by a **union-find** (disjoint-set)
structure, then solves them with **BFS** and **A\***. Output is ASCII art in the
terminal and, optionally, an SVG file. Pure Python, no runtime dependencies.

```
+---+---+---+---+---+---+---+---+
| S |   |   | *   *   * |       |
+   +   +   +   +---+   +   +---+
| *   * | *   *     | * |       |
+---+   +   +   +---+   +---+   +
|   | *   * |       | * | *   * |
+   +   +---+---+   +   +   +   +
|       |           | *   * | * |
+   +   +---+   +---+---+   +   +
|   |       |           |   | E |
+---+---+---+---+---+---+---+---+

cells: 40  passages: 39  generated in 0.14 ms
bfs: path length 17, explored 38 cells, 0.08 ms
```

## CS concepts

| Concept | Where |
|---|---|
| Disjoint-set forest with **path compression** + **union by rank** (amortised O(α(n)) per op) | `unionfind.py` |
| Grid as a graph; a perfect maze **is a spanning tree** (V−1 edges, connected, acyclic) | `maze.py` |
| **Kruskal's MST** with random edge order → uniform-ish random spanning tree; cycle detection via `union()` returning `False` | `maze.generate` |
| Spanning-tree verification (edge count + union-find cycle check) | `maze.is_perfect` |
| **BFS** shortest path, O(V+E) | `solver.bfs` |
| **A\*** with an admissible Manhattan heuristic and lazy deletion in a binary heap | `solver.astar` |
| Path reconstruction from a predecessor map | `solver._reconstruct` |

Why union-find? Kruskal needs to ask "are these two cells already connected?"
for every wall. A naive flood fill makes that O(V) per wall (O(V²) overall);
union-find makes it effectively constant, so a 300×300 maze (90,000 cells)
generates in about half a second in pure Python.

The `find` is iterative (two-pass compression), so a worst-case 100,000-long
chain doesn't hit Python's recursion limit. A test covers this.

## Layout

```
src/ufmaze/
  unionfind.py   disjoint-set structure
  maze.py        Maze model, Kruskal generator, is_perfect()
  solver.py      BFS and A* solvers
  render.py      ASCII and SVG renderers
  cli.py         argparse command-line interface
tests/test_ufmaze.py
```

## Build, run, test

Needs Python 3.10+. For tests, you also need `pytest`.

```bash
# run without installing
PYTHONPATH=src python3 -m ufmaze -r 10 -c 20 --seed 7 --solve astar --stats

# or install the `ufmaze` command
pip install -e '.[dev]'
ufmaze -r 30 -c 50 --solve bfs --svg maze.svg

# tests
make test           # or: python3 -m pytest
```

Options:

| Flag | Meaning |
|---|---|
| `-r/--rows`, `-c/--cols` | maze size (default 10×20) |
| `-s/--seed` | reproducible maze |
| `--solve bfs\|astar` | draw the solution path with `*` |
| `--svg FILE` | also write an SVG (path drawn in pink) |
| `--animate` | print the maze after each wall removal, so you can watch Kruskal merge regions |
| `--stats` | timings, path length, and cells explored |

### BFS vs A\*

Both return the same (unique) path. A\* usually explores fewer cells:

```
size     path length  BFS explored  A* explored
100x100      346          9,851        6,452
300x300    1,786         75,924       75,276
```

In large perfect mazes, the gap shrinks because the single path winds far
from the straight line. The heuristic can't prune much when the maze forces
long detours.

## Tests

31 pytest cases cover:

- union-find checked against a naive relabelling model over 1,000 random operations
- `is_perfect` on generated mazes across sizes, including 1×1 and 1×N
- seed reproducibility
- cycle and disconnection detection
- BFS/A\* agreement and path validity
- unreachable goals
- ASCII wall count equals the grid edge count minus passages
- SVG well-formedness
- the CLI

## Possible extensions

- Other generators to compare the textures they produce: recursive backtracker (long corridors), Prim's (short dead ends), and Wilson's (truly uniform spanning trees).
- Weighted walls, so mazes prefer horizontal or vertical runs.
- Hex or triangular grids. Only `grid_neighbors` and the renderers change.
- Braid mazes: remove some dead ends to add loops, then compare BFS against DFS.
- Dead-end and branching-factor statistics per algorithm.
- Animated SVG/GIF export of the generation steps.
