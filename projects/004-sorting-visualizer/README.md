# Sorting Visualizer

A browser app that animates **bubble, merge, quick and heap sort** bar by bar. You can play, pause and single-step the sort. It highlights comparisons, swaps, the quick-sort pivot and the active subarray, and it counts comparisons, swaps and writes as it goes. It is plain HTML/CSS/JavaScript with no build step and no dependencies.

## Features

- Four algorithms, with a best/average/worst/space/stability table for each
- Four input shapes: random, nearly sorted, reversed and few unique. These show off best and worst cases (try bubble sort on nearly sorted input, or heap sort on reversed input)
- Size from 8 to 160 bars. The speed slider goes from 500 ms per step up to 64 steps per frame
- Play/pause, step, reset (replays the same input) and new array
- Live counters for comparisons, swaps, writes and steps
- Optional sound: the pitch follows the height of the bar being touched
- Keyboard shortcuts: <kbd>Space</kbd> play/pause, <kbd>→</kbd> step, <kbd>R</kbd> reset, <kbd>N</kbd> new array
- Light and dark themes that follow the system setting, and a responsive layout

## CS concepts demonstrated

- **Sorting algorithms and their trade-offs.** O(n²) vs O(n log n), in-place vs O(n) extra space, stable vs unstable.
- **Generators as resumable computations.** Each algorithm is a `function*` that `yield`s a step event (`compare`, `swap`, `overwrite`, `sorted`, `pivot`, `range`). This turns the algorithm into a lazy stream that can be paused at any point with no callbacks or async code. Recursive algorithms use `yield*` to delegate to their own recursive calls.
- **Separation of model and view.** `algorithms.js` and `player.js` have no DOM code and are fully unit tested. `app.js` only renders state.
- **Event sourcing / replay.** The visual state comes *only* from replaying events. The tests prove that replaying the stream reproduces a correctly sorted array.
- **Algorithm engineering details:**
  - Bubble sort exits early when a pass makes no swaps, so it is O(n) on sorted input.
  - Merge sort uses `<=` to stay stable.
  - Quick sort uses a **median-of-three** pivot, which avoids the O(n²) case on sorted input. It recurses on the smaller side first so the stack depth is O(log n).
  - Heap sort uses bottom-up **heapify** (O(n)) and then repeated sift-down.
- **Deterministic randomness.** A seeded PRNG (`mulberry32`) lets the tests generate thousands of reproducible inputs.

## Project structure

```
004-sorting-visualizer/
├── index.html          UI markup
├── styles.css          layout, bar colours, dark mode
├── src/
│   ├── algorithms.js   the four sorts as event-yielding generators + metadata
│   ├── player.js       playback engine, input generators, PRNG, speed curve
│   └── app.js          DOM wiring, rendering, timers, sound
└── test/
    ├── algorithms.test.js
    └── player.test.js
```

## Run

ES modules need to be served over HTTP; opening the file directly won't load them. From this folder, run either:

```bash
npm start                 # serves on http://localhost:5173 (uses npx serve)
# or
python3 -m http.server 5173
```

Then open http://localhost:5173.

## Test

The tests need Node 18 or newer and use the built-in `node:test` runner, so there is nothing to install.

```bash
npm test
```

The 34 tests check the following:

- Every algorithm sorts edge cases (empty, one element, duplicates, negatives) and hundreds of seeded random inputs of every shape, purely by replaying its events.
- Every index is marked sorted exactly once, every event index is in bounds, and the input array is never mutated.
- Bubble sort makes exactly n−1 comparisons on sorted input, and its swap count equals the number of inversions.
- Merge sort makes exactly n·log₂n writes for n = 2^k.
- Quick sort makes O(n log n) comparisons on already-sorted input, thanks to median-of-three.
- The O(n log n) sorts use more than 5× fewer comparisons than bubble sort at n = 300.
- The player's stepping, reset, highlight lifetime and pivot tracking behave correctly, and the speed curve is monotonic.

Example output:

```
# tests 34
# pass 34
# fail 0
```

## Example comparison counts

These are counts from one random 48-bar run at full speed:

| Algorithm | Comparisons |
|-----------|-------------|
| Bubble    | ~1,100      |
| Heap      | ~390        |
| Quick     | ~280        |
| Merge     | ~200        |

## Possible extensions

- **Race mode.** Run all four algorithms side by side on the same input.
- More algorithms: insertion, selection, shell, counting/radix (non-comparison), Timsort, introsort.
- A scrubbable timeline that records events into an array so you can step *backwards*.
- A pseudocode panel that highlights the line currently executing.
- Let users type in a custom array, or share a seed via the URL.
- Draw on `<canvas>` so arrays with thousands of elements stay smooth.
