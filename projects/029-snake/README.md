# 029 · Snake

Classic Snake in vanilla JavaScript and the HTML5 Canvas, with five levels and a persistent high-score table. No dependencies, no build step.

## Features

- **Five levels**, each faster and worth more points per food:
  | # | Name | Tick | Food to advance | Edges |
  |---|------|------|-----------------|-------|
  | 1 | Open Field | 140 ms | 5 | wrap |
  | 2 | Fenced In | 120 ms | 6 | walls |
  | 3 | Twin Bars | 105 ms | 7 | walls |
  | 4 | The Cross | 90 ms | 8 | wrap |
  | 5 | Rooms | 75 ms | endless | walls |
- **High scores**: top 10 saved in `localStorage` (falls back to memory if storage is blocked).
- Keyboard (arrows / WASD, P or Space to pause, Enter to continue) and swipe controls on touch screens.
- High-DPI canvas rendering and a pulsing food marker.

## CS concepts

- **Separation of logic and presentation**: `src/game.js` is a pure state machine with no DOM or timers, so it runs unchanged in Node tests.
- **Fixed-timestep game loop**: `requestAnimationFrame` renders every frame while an accumulator advances logic at the level's tick rate, independent of monitor refresh rate. The delta is clamped so a background tab doesn't fast-forward.
- **Finite state machine**: `ready → running ⇄ paused → won-level / over`.
- **Input buffering**: a small turn queue lets quick "up, left" presses land on consecutive ticks, and reversal checks run against the last *queued* direction so you can't turn into yourself.
- **Collision detection with sets**: walls are a `Set` of `"x,y"` keys for O(1) lookups; the tail cell is excluded when it's about to move, so chasing your own tail is legal.
- **Dependency injection**: the RNG and the storage backend are passed in, which makes food placement and persistence deterministic in tests.
- **Defensive persistence**: corrupt JSON, tampered entries and quota errors are handled without crashing.

## Project layout

```
index.html          page shell
styles.css          layout and theme
src/game.js         pure game rules (movement, growth, collisions, levels)
src/levels.js       level configs and wall generators
src/highscores.js   top-10 table over a Storage-like backend
src/renderer.js     canvas drawing
src/main.js         input, game loop, wiring
test/               node:test suites
```

## Run

ES modules need to be served over HTTP (not `file://`):

```bash
npm start            # serves on http://localhost:5173
# or: python3 -m http.server 5173
```

## Test

Requires Node 18+. No packages to install.

```bash
npm test
```

```
# tests 25
# pass 25
# fail 0
```

The suites cover movement, wrapping, wall and self collisions, tail-chasing, the input queue, growth and scoring, level progression, that every level spawns the snake safely at several grid sizes, food spawning on a full board, pausing, and the high-score table (ordering, ties, capping, persistence, sanitising bad data, storage failures).

## Possible extensions

- Sound effects with the Web Audio API.
- Power-ups (slow-motion, shrink, score multiplier) with timed expiry.
- A level editor that serialises wall layouts to JSON.
- An AI autopilot using BFS / A* toward the food, with a fallback that follows its own tail.
- Two-player mode on a shared keyboard.
