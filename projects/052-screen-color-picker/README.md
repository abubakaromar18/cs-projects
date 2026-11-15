# 052 · Screen Color Picker

A Tkinter desktop app for picking a color from anywhere on your screen and
converting it between HEX, RGB, HSL, HSV, CMYK and the nearest CSS color name.
It also shows WCAG contrast ratios, color-wheel harmonies and a persistent
history. A small CLI does the same conversions headless.


```
┌──────┐ Color (hex, rgb(), hsl(), name):
│swatch│ [#3366FF            ]
└──────┘
RGB      R ──●────────  G ────●──────  B ─────────●
Formats  HEX  #3366FF                 [Copy]
         RGB  rgb(51, 102, 255)       [Copy]
         HSL  hsl(225, 100%, 60%)     [Copy]   … HSV, CMYK, Name
Contrast vs white 4.68:1 (AA)   vs black 4.49:1 (AA large)
Harmonies  complementary ■■  analogous ■■■  triadic ■■■  …
History    ■ ■ ■ ■
[Pick from screen (Ctrl+P)] [System chooser…]        [Clear history]
```

## Features

- **Pick from screen** – hides the window, takes a screenshot, and shows it
  full-screen with a 15×15 magnifying **loupe**. Click (or Enter) to pick,
  arrow keys nudge one pixel, mouse wheel switches between 1×1, 3×3, 5×5…
  averaging, Esc cancels.
- **Type any color** – `#f80`, `ff8800`, `rgb(255 136 0)`, `rgb(100%,0%,50%)`,
  `hsl(32, 100%, 50%)`, `hsv(...)`, or a name like `tomato`.
- Live **RGB sliders**, one-click **Copy** for every format (Ctrl+C copies HEX).
- **WCAG 2.x contrast** against white and black with AA/AAA grading.
- **Harmonies**: complementary, analogous, triadic, split-complementary,
  tetradic, shades and tints — click any swatch to jump to it.
- **History** of the last 16 colors, saved to `~/.config/colorpick/history.json`.

## CS concepts demonstrated

| Concept | Where |
| --- | --- |
| Color-space conversion (sRGB ↔ HSV/HSL/CMYK) and round-tripping | `colors.py` |
| sRGB gamma linearization & WCAG relative luminance | `relative_luminance` |
| Perceptual distance ("redmean") + nearest-neighbour search | `nearest_named` |
| Hue rotation on the color wheel (modular arithmetic) | `harmonies` |
| Parsing user input with regexes & validation | `parse_color` |
| Box-filter averaging with edge clipping | `sampler.sample` |
| Observer pattern / single source of truth for the UI | `model.PickerModel` |
| Bounded MRU cache (`deque(maxlen)`) + atomic file writes | `history.py` |
| Event-driven GUI, key/mouse bindings, re-entrancy guard | `app.py` |
| Dependency injection for testability (fake screen grabber) | `ColorPickerApp(grabber=…)` |

## Project layout

```
src/colorpick/
  colors.py    pure color math (no Tk)
  sampler.py   pixel sampling + loupe grid, Pillow screen capture
  history.py   MRU history with JSON persistence
  model.py     observable app state
  app.py       Tkinter views: main window + full-screen picker overlay
  cli.py       argparse CLI (GUI is the default sub-command)
tests/         pytest suite (GUI tests auto-skip without a display)
```

## Build, run, test

Requires Python ≥ 3.10 with Tk (on Debian/Ubuntu: `sudo apt install python3-tk`).
Screen capture uses Pillow (Windows, macOS, and X11 Linux; Wayland sessions
may block screenshots — the rest of the app still works).

```bash
make install          # pip install -e ".[dev]"
make run              # or: colorpick
make test             # unit tests (GUI tests skip when headless)
make gui-test         # Linux: GUI smoke tests on a virtual display via xvfb-run
```

All 46 tests pass, including the GUI smoke tests under `xvfb-run`, which
drive the real window and simulate a screen pick with a fake screenshot.

## CLI examples

```
$ colorpick convert "hsl(210, 80%, 50%)"
HEX   #197FE6
RGB   rgb(25, 127, 230)
HSL   hsl(210, 80%, 50%)
HSV   hsv(210, 89%, 90%)
CMYK  cmyk(89%, 45%, 0%, 10%)
Name  dodgerblue

$ colorpick contrast "#333" white
12.63:1  AAA

$ colorpick harmony tomato
complementary        #FF6347 #47E3FF
triadic              #FF6347 #47FF63 #6347FF
...
```

## Possible extensions

- Global hotkey to pick without focusing the app (e.g. via `pynput`).
- Convert through CIELAB and use ΔE2000 for better nearest-name matching.
- Alpha channel support (`rgba()`, `#rrggbbaa`).
- Palette export to CSS variables, Tailwind config, or `.ase` swatch files.
- Color-blindness simulation (protanopia/deuteranopia matrices) of the palette.
