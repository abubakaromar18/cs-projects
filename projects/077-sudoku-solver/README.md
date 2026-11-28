# 077 · Sudoku Solver

A fast, dependency-free Sudoku solver in Python that combines **backtracking
search** with **constraint propagation**. It ships with a plain backtracking
solver for comparison, a uniqueness checker, a pencil-mark hint mode and a
generator for new unique-solution puzzles.

## What it does

- `solve` – solves a puzzle in line or grid format, optionally printing search stats
- `check` – reports conflicting givens, or whether the puzzle has 0 / 1 / many solutions
- `hint` – prints the candidates left in every cell after propagation
- `generate` – builds a random, symmetric puzzle with exactly one solution
- `bench` – compares naive backtracking and propagation on a folder of puzzles

## CS concepts

| Concept | Where |
|---|---|
| Constraint satisfaction problem (variables, domains, constraints) | `board.py` precomputes the 27 units and 20 peers per cell |
| Depth-first backtracking | `solve_naive` and `_search` in `solver.py` |
| Constraint propagation to a fixed point | `_State.assign` – a work queue of forced assignments |
| Naked singles / hidden singles | peer elimination in `assign`, `_hidden_singles` |
| MRV (minimum remaining values) heuristic | `_State.best_cell` |
| Bitset domains | each cell's candidates are a 9-bit mask (`cand[i]`) |
| Generators for lazy enumeration | `solutions()` yields solutions; `count_solutions(limit=2)` tests uniqueness without a full search |
| Copy-on-branch state | each guess works on a copy, so undo is free |

### How propagation works

Every cell starts with candidates `{1..9}`. Placing a digit removes it from the
cell's 20 peers. If that leaves a peer with one candidate (a *naked single*)
it's queued and placed too. When the queue empties, the solver scans each unit
for a digit with only one possible cell (a *hidden single*). This repeats until
nothing changes. A cell with no candidates, or a digit with nowhere to go in a
unit, is a contradiction and the branch is abandoned.

Only when propagation stalls does the solver guess, and it guesses in the cell
with the fewest candidates. The easy puzzle below is solved with **zero
guesses**.

## Build, run, test

Requires Python 3.10+. No runtime dependencies.

```bash
make install        # pip install -e ".[dev]"  (installs the `sudoku` command)
make test           # python -m pytest
make demo           # solve puzzles/hard.txt with stats
make bench          # naive vs propagation on puzzles/
```

Without installing: `PYTHONPATH=src python -m sudoku solve puzzles/easy.txt`.

### Input format

Either 81 characters on one line, or a grid. Digits are givens; `.`, `0` or `_`
are blanks; `| - +` and whitespace are ignored; lines starting with `#` are
comments. See `puzzles/grid.txt`.

## Example

```
$ sudoku solve puzzles/hard.txt --stats
4 1 7 | 3 6 9 | 8 2 5
6 3 2 | 1 5 8 | 9 4 7
9 5 8 | 7 2 4 | 3 1 6
------+-------+------
8 2 5 | 4 3 7 | 1 6 9
7 9 1 | 5 8 6 | 4 3 2
3 4 6 | 9 1 2 | 7 5 8
------+-------+------
2 8 9 | 6 4 3 | 5 7 1
5 7 3 | 2 9 1 | 6 8 4
1 6 4 | 8 7 5 | 2 9 3
nodes=16 guesses=25 backtracks=10 propagated=119 time=5.0ms

$ sudoku bench puzzles/
puzzle        method             nodes   guesses        ms
easy          naive               4209      4208      22.3
easy          propagation            1         0       3.2
hard          naive            200001+    200000    1010.6
hard          propagation           16        25       5.2
inkala        naive              49559     49558     240.8
inkala        propagation          136       264      28.3
('+' = naive search hit the node limit)
```

The "hard" puzzle (one of Peter Norvig's examples) needs over 200,000 nodes
with plain backtracking. With propagation it needs 16. `inkala.txt` is Arto
Inkala's "world's hardest Sudoku".

```
$ sudoku check puzzles/easy.txt
unique solution
```

## Project layout

```
src/sudoku/
  board.py      geometry (units, peers), parse/format, validity checks
  solver.py     naive backtracking + propagation/MRV solver, uniqueness
  generator.py  unique-solution puzzle generator
  cli.py        argparse front end
tests/          pytest suite (29 tests)
puzzles/        sample puzzles
```

## Possible extensions

- More human techniques: naked/hidden pairs, pointing pairs, X-Wing. Log
  each step to explain the solution.
- Rate difficulty by the hardest technique a puzzle needs.
- Dancing Links (Knuth's Algorithm X) as an exact-cover solver, and a
  benchmark against this one.
- Support other sizes (16×16) and variants (diagonal, killer).
- A curses or web UI for playing with hints.
