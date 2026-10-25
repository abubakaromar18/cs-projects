# Tic-Tac-Toe With Minimax

A tic-tac-toe game with an **unbeatable AI**, played in a pygame window (or in the terminal).
The AI solves the game tree with minimax; an alpha-beta version is included to show how much
work pruning saves.

## Features

- pygame UI: click to move, winning line highlight, running score, undo, swap sides
- Three difficulty levels: `easy` (random, but takes a free win), `medium` (perfect 70% of the time), `hard` (perfect)
- **Hint mode** (`H`): labels each empty cell *win / draw / lose* using the minimax value
- Terminal mode (`--cli`) with the same engine
- `--analyze` prints the value of every move in any position
- `--stats` compares node counts for plain minimax vs. alpha-beta

## CS concepts

| Concept | Where |
|---|---|
| Game trees and **minimax** (negamax form) | `ai.py: negamax` |
| **Alpha-beta pruning** and move ordering | `ai.py: alphabeta`, `MOVE_ORDER` |
| **Memoisation / transposition table** | `@lru_cache` on `negamax`, possible because `Board` is immutable and hashable |
| Depth-aware scoring (win fast, lose slowly) | `terminal_score`: `±(1 + empty cells)` |
| Exhaustive verification | tests walk every opponent reply to prove the AI never loses |
| Separating model, controller and view | `board.py` / `game.py` / `gui.py` + `cli.py` |

### How the AI scores positions

Scores are from the view of the player to move. A finished game where the opponent just won is
worth `-(1 + empty cells)`; a draw is `0`. Each position's value is the max over moves of
`-value(child)`. Since quicker wins leave more empty cells, the AI prefers them, and when it
is lost (only possible on `easy`/`medium`) it delays the loss.

## Layout

```
src/tictactoe/
  board.py   immutable Board: moves, win detection, parsing
  ai.py      negamax (cached), alphabeta (instrumented), AIPlayer difficulties
  game.py    UI-independent controller: turns, score, undo, new rounds
  gui.py     pygame front end
  cli.py     argparse entry point, terminal game, --analyze, --stats
tests/       pytest suite (GUI tests run headless with SDL's dummy driver)
```

## Build, run, test

Requires Python 3.10+.

```bash
make dev            # pip install -e '.[dev]'  (installs pygame + pytest)
make run            # open the pygame window
make cli            # play in the terminal
make test           # 40 tests, headless
make stats
```

After `pip install .` you also get a `tictactoe` command:

```bash
tictactoe                       # GUI, you are X, hard AI
tictactoe --play-as O -d medium
tictactoe --cli
tictactoe --analyze "XX.OO...."
```

**GUI controls:** click = move · `R`/Space new round · `U` undo · `S` swap sides · `H` hints ·
`1`/`2`/`3` difficulty · `Esc`/`Q` quit.

## Example output

```
$ tictactoe --stats
Value of the empty board: 0 (a draw with perfect play)
Plain minimax visits  549,946 nodes
Alpha-beta visits       7,865 nodes (2,854 cutoffs, 98.6% pruned)

$ tictactoe --analyze "XX.OO...."
 X | X | 3
---+---+---
 O | O | 6
---+---+---
 7 | 8 | 9

X to move. Move values (+ win, 0 draw, - loss):
  cell 3: +5
  cell 6: +0
  cell 7: -4
  cell 8: -4
  cell 9: -4
```

## Tests

The suite checks the known facts about tic-tac-toe (5,478 reachable positions, a 549,946-node
full tree, the empty board is a draw), checks that alpha-beta matches minimax on every reachable
position, and plays the hard AI against **every possible opponent line**, as X and as O, to
prove it never loses. The pygame UI is tested headless with `SDL_VIDEODRIVER=dummy`.

## Possible extensions

- Use board symmetries (8 rotations/reflections) to shrink the transposition table
- Generalise to *m,n,k* games (e.g. 4×4 or Gomoku) with depth-limited search and a heuristic
- Iterative deepening, or Monte Carlo Tree Search for comparison
- Animate moves and add sound effects
- Two-player hot-seat and network play modes
