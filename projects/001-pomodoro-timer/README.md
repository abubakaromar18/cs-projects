# 001 · Pomodoro Timer

A focus timer built with plain **HTML, CSS and JavaScript** (no frameworks, no build step). It runs Pomodoro cycles of focus sessions and short/long breaks, plays synthesised sound alerts, sends optional desktop notifications, and keeps stats (today's sessions, focus time, a day streak and a 7-day chart) in `localStorage`.

## Features

- Focus / short break / long break phases, with a long break every N sessions (default 25/5/15, every 4)
- Start, pause/resume, reset and skip, plus keyboard shortcuts (`Space`, `R`, `S`)
- Animated progress ring, phase-coloured theme, light and dark mode
- Sound alerts generated with the Web Audio API (no audio files), adjustable volume
- Optional browser notifications when a phase ends
- Stats: sessions today, focus minutes today, day streak, all-time total, 7-day bar chart
- Configurable durations and auto-start, saved between visits
- Accurate in background tabs: time comes from timestamps, not counted ticks

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Finite state machine** (idle → running → paused, phase transitions) | `src/timer.js` |
| **Wall-clock vs. tick-based timing**: storing `endsAt` so throttled `setInterval` calls don't make the timer drift | `PomodoroTimer.getRemaining()` |
| **Dependency injection** of the clock and storage so the logic is deterministic and testable | `new PomodoroTimer({ now })`, `new SessionLog(storage)` |
| **Observer pattern**: a small event emitter (`on`/`emit`) decouples logic from rendering | `timer.on('complete', …)` |
| **Separation of concerns**: pure logic modules vs. a thin DOM layer | `timer.js`, `stats.js` vs. `app.js` |
| **Aggregation over an append-only event log** (group by day, streaks) | `src/stats.js` |
| **Defensive persistence**: validating stored JSON and falling back when storage throws | `SessionLog.load()/save()` |
| **Digital sound synthesis**: oscillators and gain envelopes | `src/sound.js` |

## Project structure

```
001-pomodoro-timer/
├── index.html        # markup
├── styles.css        # theme, layout, phase colours, dark mode
├── src/
│   ├── timer.js      # state machine (pure, no DOM)
│   ├── stats.js      # session log + aggregations (pure, storage-agnostic)
│   ├── sound.js      # Web Audio alerts
│   └── app.js        # DOM wiring and rendering
├── test/
│   ├── timer.test.js
│   └── stats.test.js
└── package.json
```

## Run

ES modules need to be served over HTTP (opening `index.html` as a `file://` URL won't load them). Any static server works:

```bash
npm start                      # npx serve on http://localhost:5173
# or
python3 -m http.server 5173    # then open http://localhost:5173
```

## Test

Tests use Node's built-in test runner (Node 18+), so there are no dependencies to install:

```bash
npm test
```

```
# tests 22
# pass 22
# fail 0
```

The tests cover formatting, settings validation, the long-break schedule, pause/resume timing with a fake clock, the full 8-phase cycle, skip/reset/auto-start, streak and per-day aggregation, and recovery from corrupt or unavailable storage.

## Example: using the timer core on its own

```js
import { PomodoroTimer, formatTime } from './src/timer.js';

const timer = new PomodoroTimer({ settings: { workMinutes: 50, shortBreakMinutes: 10 } });
timer.on('tick', (s) => console.log(s.phase, formatTime(s.remaining)));
timer.on('complete', (e) => console.log(`${e.phase} done, next: ${e.next}`));
timer.start();
setInterval(() => timer.tick(), 1000);
// work 49:59
// work 49:58
// …
```

## Possible extensions

- Task list: attach each focus session to a named task and show time per task
- Export/import stats as CSV or JSON
- A service worker so the app works offline and installs as a PWA
- Make the timer more reliable in the background using a Web Worker
- A full-year activity heatmap (like a GitHub contributions graph)
- Custom sound packs or a ticking sound during focus sessions
