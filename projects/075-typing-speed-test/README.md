# Typing Speed Test

A browser typing test (TypeScript, no frameworks) that measures **net/raw WPM, accuracy and
rhythm consistency**, charts your speed over time, and draws a **per-key heatmap** on a QWERTY
keyboard showing which keys you miss most or hit slowest. It remembers your runs, tracks
personal bests per mode, and can generate an **adaptive practice passage** that targets your
weakest keys.

## Features

- Word-count modes (10 / 25 / 50) and timed modes (15 / 30 / 60 s)
- Optional punctuation (capitalised sentences, `, . ? !`) and numbers
- Live WPM, accuracy and progress/countdown
- Results: net WPM, raw WPM, accuracy, consistency, correct / wrong / fixed characters
- SVG chart of cumulative net WPM, per-bucket burst WPM and error markers
- Keyboard heatmap in **errors** or **latency** mode, for **this run** or **lifetime**
- "Practise weak keys": next passage is biased toward words containing your worst keys
- History of recent runs and personal bests in `localStorage` (fails safe if blocked)
- `Tab`/`Esc` to restart, `Ctrl+Backspace` to delete a word; light and dark themes

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Event-sourced state**: every keystroke is logged with a timestamp; all stats (incl. the timeline) are derived by replaying the log | `src/core/session.ts` |
| **Pure core / imperative shell**: time is injected (`at` ms) so the engine is deterministic and unit-testable; the DOM layer is thin | `session.ts` vs `src/web/app.ts` |
| **Finite state machine**: `ready → running → finished` | `TypingSession.state` |
| **Seeded PRNG** (mulberry32) for reproducible passages | `src/core/random.ts` |
| **Bayesian / Laplace smoothing** so one miss on a rarely-seen key isn't shown as 100% red | `src/core/heatmap.ts` |
| **Statistics**: coefficient of variation of inter-key intervals → consistency score; latency capping to reject outliers | `consistency()`, `keyStats()` |
| **Weighted sampling** for adaptive practice (words duplicated by number of weak keys they contain) | `buildFocusPool()` |
| **Incremental DOM updates**: only spans between the old and new cursor are re-classed | `updateSpans()` |
| **Defensive I/O**: versioned, validated persistence that tolerates corrupt/blocked storage | `src/core/history.ts` |
| **Path-traversal-safe static server** bound to localhost | `src/server/serve.ts` |

### Scoring definitions

- A "word" is 5 characters (spaces included).
- **Raw WPM** = characters in the buffer / 5 / minutes.
- **Net WPM** = *correct* characters in the buffer / 5 / minutes — uncorrected errors cost speed.
- **Accuracy** = correct character keystrokes / all character keystrokes — fixed errors still count against you.
- **Consistency** = `100 × (1 − stddev/mean)` of the gaps between keystrokes, clamped to 0–100.
- Per-key misses are charged to the key you were *supposed* to press; latency is measured only on correct hits and pauses over 2 s are ignored.

## Project layout

```
src/
  core/            pure logic, runs in Node and the browser
    session.ts     TypingSession engine: keystroke log, stats, timeline, per-key stats
    passage.ts     passage generator (punctuation, numbers, focus keys)
    keyboard.ts    US QWERTY model, char → physical key mapping
    heatmap.ts     heatmap model, colour ramp, weakest-key ranking, stat merging
    history.ts     persisted runs / personal bests / lifetime key stats
    random.ts      mulberry32 PRNG helpers
    words.ts       word list
  web/
    app.ts         DOM wiring and rendering
    format.ts      formatting and chart geometry (pure)
  server/
    serve.ts       tiny localhost static server for development
public/            index.html, styles.css
test/              node:test suites
```

## Build, run, test

Requires Node 18+.

```bash
npm install
npm start          # builds, then serves http://127.0.0.1:5175/
npm test           # compiles and runs 36 node:test tests
npm run typecheck
```

`PORT=8080 npm start` or `node dist/server/serve.js --port 8080` to change the port. The server
only binds to `127.0.0.1`.

## Example

After a 25-word run:

```
Results                     New personal best!
  72 net wpm   76 raw wpm   96% accuracy   84% consistency   20.8s   125/0/5

Weakest keys: b v q y p · Slowest: q (412 ms), z (380 ms), p (301 ms)
```

The heatmap colours each key from green (fine) to red (≥ 25% smoothed miss rate, or slowest key
in latency mode). Hover a key for `hits/attempts` and its average latency.

## Possible extensions

- Alternative layouts (Dvorak, Colemak) — `keyboard.ts` is data-driven
- Bigram/trigram analysis (e.g. "slow on `th`") and n-gram-targeted practice
- Quote mode with real text, or code mode with brackets and indentation
- Export history as CSV; a lifetime WPM trend chart
- Replay a run character-by-character from the keystroke log
