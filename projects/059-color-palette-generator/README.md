# Color Palette Generator

A Svelte 5 web app for generating, locking, and exporting **accessible** color palettes. Press <kbd>Space</kbd> to roll a new palette built from a color-harmony rule, lock the colors you like, check every text/background pairing against WCAG contrast rules, auto-fix failing pairs, and export to CSS, SCSS, JSON, Tailwind, or SVG.

## Features

- **Harmony modes:** analogous, complementary, split-complementary, triadic, tetradic, monochromatic, or fully random.
- **Locking:** locked swatches stay put when you regenerate, and the first locked color becomes the base hue for the harmony.
- **Edit colors** with the native color picker, or double-click a hex code and type one. Reorder, add (up to 10), and remove (down to 2) swatches.
- **Accessibility:** each swatch shows its contrast ratio with black and white text and the WCAG rating (AAA / AA / AA Large / Fail). A pairwise **contrast matrix** shows which palette colors work together, and a **fix** button nudges a failing text color's lightness just far enough to pass AA.
- **Undo/redo** for every edit (<kbd>Ctrl/⌘+Z</kbd>, <kbd>Ctrl/⌘+Shift+Z</kbd>).
- **Shareable URLs:** the palette lives in the URL hash (`#112233-!aabbcc-ffffff`, where `!` marks a locked color).
- **Export** to CSS custom properties, SCSS variables, JSON (hex, RGB, and HSL), a Tailwind `colors` snippet, or an SVG strip. You can copy it or download it.
- Responsive layout (swatches stack on narrow screens) and a dark mode that follows your system setting.

## Key CS concepts

| Concept | Where |
|---|---|
| Color-space conversion (sRGB ↔ HSL hexcone model) | `src/lib/color.js` |
| WCAG relative luminance (gamma linearisation, weighted sum) and contrast ratio | `src/lib/color.js` |
| **Binary search** over a continuous domain (minimal lightness change to reach a contrast target) | `ensureContrast` in `color.js` |
| **Seeded PRNG** (mulberry32) for reproducible, testable randomness | `src/lib/random.js` |
| Rule-based generation (hue offsets on the color wheel and a lightness ladder) | `src/lib/palette.js` |
| Immutable state and the **two-stack undo/redo** design | `src/lib/history.js` |
| Serialisation and validating parsing (URL-hash encoding) | `encodePalette` / `decodePalette` |
| Fine-grained reactivity (Svelte 5 runes: `$state`, `$derived`, `$effect`) | `src/App.svelte`, `src/components/` |

The color logic is kept in plain JS modules with no Svelte dependency, which keeps it fully unit-testable. The components only handle presentation and events.

## Project structure

```
src/
  main.js               mounts the app
  App.svelte            state, history, URL sync, keyboard shortcuts
  app.css               theme tokens and base styles
  components/
    Swatch.svelte       one color column with its controls and contrast info
    ContrastGrid.svelte pairwise WCAG matrix with "fix" actions
    ExportPanel.svelte  format tabs, copy, and download
  lib/
    color.js            conversions, luminance, contrast, ensureContrast
    palette.js          harmonies, generation, editing ops, URL encoding
    exporters.js        CSS / SCSS / JSON / Tailwind / SVG
    history.js          undo/redo
    random.js           mulberry32 seeded RNG
test/                   Vitest suites for all lib modules
```

## Build, run, test

Requires Node 20 or later.

```bash
npm install
npm run dev       # http://localhost:5173
npm test          # vitest: 35 tests
npm run build     # production bundle in dist/
npm run preview   # serve the built bundle
```

Example test run:

```
 Test Files  3 passed (3)
      Tests  35 passed (35)
```

## Example

Open `http://localhost:5173/#112233-!aabbcc-ffffff`. Swatch 2 (`#aabbcc`) is locked. Pressing Space keeps it and regenerates the other two around its hue. The contrast matrix flags `#aabbcc` on white as **2.0 · Fail** and offers **fix → #5b7998**, which is the same hue, darkened just enough to reach 4.5:1.

The CSS export of that palette:

```css
:root {
  --color-1: #112233;
  --color-2: #aabbcc;
  --color-3: #ffffff;
}
```

## Possible extensions

- Generate in a perceptual space (OKLCH) so equal steps look equally different.
- Color-blindness simulation (protanopia, deuteranopia, tritanopia) using Brettel/Viénot matrices.
- Extract a palette from an uploaded image with k-means clustering.
- Generate full tint/shade scales (50–950) for each swatch.
- Save named palettes to localStorage, and add drag-and-drop reordering.
- APCA contrast (the WCAG 3 draft) alongside WCAG 2.
