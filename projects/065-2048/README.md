# 2048

The classic sliding-tile puzzle, written in **TypeScript** with no runtime dependencies.
Slide the board with arrow keys or a swipe; equal tiles merge, and the goal is to build a 2048 tile.

- Keyboard (arrows / WASD / HJKL) and touch or mouse **swipe controls**
- **Animations**: tiles slide via CSS transitions, merged tiles "pop", new tiles fade in, the score shows a floating `+N`, and an invalid move shakes the board
- One-step **undo**, win screen with "keep going", game-over detection
- **Best score and the current game are saved** in `localStorage`, and the game still works if storage is blocked
- Respects `prefers-reduced-motion`

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Separating the pure model from the view.** The engine has no DOM code, and the renderer only reads a `MoveResult` | `src/game.ts`, `src/renderer.ts` |
| **Grid traversal by direction vector.** One merge routine serves all four directions by walking each line from its leading edge | `Game.lines()` / `Game.move()` |
| **Single-pass merge with a "merged once" flag.** This gives `[2,2,2,2] → [4,4]` and `[4,2,2] → [4,4]`, never a chain into 8 | `Game.move()` |
| **Stable identities for animation.** Every tile has an id, and a move reports `(id, from, to)` slides plus merges as `sources → new id`. This is the keyed-reconciliation idea behind virtual-DOM frameworks | `TileMove`, `TileMerge`, `Renderer.animate()` |
| **Dependency injection for determinism.** The RNG and storage are passed in, so the tests are exact | `GameOptions.rng`, `KeyValueStore` |
| **Snapshots (the memento pattern)** for undo and save/restore | `Game.snapshot()` / `restore()` |
| **Gesture classification.** Distance threshold, dominant-axis ratio and a time limit | `src/input.ts` |
| **Defensive parsing** of persisted JSON with a type guard | `src/storage.ts` |

## Project layout

```
065-2048/
├── index.html          # page shell, loads dist/main.js as an ES module
├── styles.css          # board layout, tile colours, animations
├── src/
│   ├── game.ts         # pure engine: move/merge, spawn, win/lose, undo, snapshots
│   ├── input.ts        # key mapping + swipe detection (pure functions)
│   ├── storage.ts      # best score + saved game over a Storage-like interface
│   ├── renderer.ts     # keyed DOM renderer that animates MoveResults
│   └── main.ts         # wiring: events → engine → renderer
└── test/               # node:test suites for game, input, storage
```

## Build, run, test

Requires Node 18+.

```bash
npm install
npm test          # compiles src + tests with tsc, runs node --test (40 tests)
npm start         # builds to dist/ and serves at http://localhost:5173
```

`npm run typecheck` checks types without writing any output. You can also run `npm run build` and serve the folder with any static server. Opening `index.html` straight from disk won't work, because browsers block ES modules on `file://`.

## Example

```ts
import { Game } from "./src/game.js";

const g = Game.fromGrid([
  [2, 2, 4, 4],
  [0, 0, 0, 0],
  [0, 0, 0, 0],
  [0, 0, 0, 0],
]);
const r = g.move("left");
g.toGrid()[0];      // [4, 8, 0, 0]
r.scoreGained;      // 12
r.merges;           // [{ id: 5, value: 4, at: {row:0,col:0}, sources: [1,2] }, ...]
r.spawned;          // the new random tile
```

Test output:

```
# tests 40
# suites 10
# pass 40
# fail 0
```

## Possible extensions

- An **AI solver** using expectimax with heuristics for monotonicity, smoothness and empty cells
- **Multi-level undo** using a bounded stack of snapshots
- A board-size picker (the engine already supports any N ≥ 2) and a configurable target
- **Seeded RNG** (e.g. mulberry32) to make daily challenges shareable
- Move history replay, and an export to an animated GIF
- A PWA manifest and service worker for offline play
