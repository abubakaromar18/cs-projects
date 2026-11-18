# Graph Plotter

An interactive function plotter in vanilla JavaScript (no dependencies). Type
expressions like `sin(x)`, `x^2/4 - 2` or `tan(x)`, then drag to pan and scroll
to zoom. Everything from parsing the math to choosing tick labels is
hand-written.

## Features

- Multiple functions at once, each in its own colour, with live error messages
  as you type (`Unexpected end of expression at position 2`)
- Pan by dragging, zoom with the wheel about the cursor, Shift/Alt + wheel to
  zoom one axis only, pinch-to-zoom on touch screens
- Keyboard: arrow keys pan, `+`/`-` zoom, `0` resets (click the plot first)
- Hover readout showing `x` and every function's `y` at the cursor
- Correct handling of discontinuities: `tan(x)`, `1/x` and `floor(x)` are not
  joined by bogus vertical lines; `sqrt(x)` stops cleanly at its domain edge
- Plots are saved in the URL hash, so a link reproduces them
  (e.g. `index.html#sin(x);cos(x)`)
- Light and dark themes following the OS setting

## CS concepts demonstrated

| Concept | Where |
| --- | --- |
| **Lexical analysis** — characters → tokens, with source positions for errors | `src/lexer.js` |
| **Recursive-descent parsing** — one function per grammar rule, precedence and right-associative `^`, unary minus below `^` so `-x^2 = -(x^2)`, implicit multiplication | `src/parser.js` |
| **ASTs and compilation to closures** — the tree is turned once into nested JS closures (no `eval`), with names and arities resolved at compile time | `src/compiler.js` |
| **Affine transforms** — world ↔ screen mapping, zoom about a fixed point `b' = p + (b − p)·k`, immutable value objects | `src/viewport.js` |
| **Adaptive sampling** — recursive bisection wherever the chord error exceeds half a pixel | `src/sampler.js` |
| **Discontinuity detection by bisection** — a continuous function's Δy → 0 as Δx → 0; across a pole or jump it doesn't | `src/sampler.js` |
| **"Nice numbers" for axes** — tick steps of 1, 2 or 5 × 10ⁿ (Heckbert's method), no floating-point drift | `src/ticks.js` |
| **Rendering** — HiDPI canvas, rAF-coalesced redraws, pointer events | `src/renderer.js`, `src/app.js` |

### Grammar

```
expr    := term (('+' | '-') term)*
term    := unary (('*' | '/') unary | implicit-factor)*
unary   := ('-' | '+') unary | power
power   := primary ('^' unary)?
primary := number | identifier | identifier '(' args ')' | '(' expr ')'
```

Functions: `sin cos tan asin acos atan sinh cosh tanh sec csc cot sqrt cbrt abs
exp ln log log2 floor ceil round sign atan2 mod min max`. Constants: `pi e tau`.

## Run

It's a static site using ES modules, so it needs to be served over HTTP (not
opened as a `file://` URL):

```bash
npm start            # serves on http://localhost:5173 (uses npx serve)
# or
python3 -m http.server 5173
```

## Test

Requires Node 18+. No dependencies to install.

```bash
npm test
```

```
# tests 28
# pass 28
# fail 0
```

The tests cover the lexer, parser precedence/associativity, implicit
multiplication, error messages, evaluation, viewport maths (round trips, zoom
fixed point, panning, clamping), tick generation/formatting, and the sampler
(chord-error bound, asymptotes of `tan` and `1/x`, steps of `floor`, the domain
edge of `sqrt`).

## Example

```js
import { compile } from './src/compiler.js';
import { sample } from './src/sampler.js';
import { Viewport } from './src/viewport.js';

const f = compile('2x^2 - 3sin(x)');
f(1);                       // 2 - 3·sin(1) ≈ -0.524

const vp = new Viewport({ xMin: -10, xMax: 10, yMin: -10, yMax: 10, width: 400, height: 400 });
sample(compile('tan(x)'), vp).length;   // 7 separate pieces between the asymptotes
```

## Possible extensions

- Symbolic differentiation on the AST and plotting `f'(x)` alongside `f`
- Root and extremum finding (bisection / Newton's method) with markers
- Parametric `(x(t), y(t))` and polar `r(θ)` curves
- Implicit curves `F(x, y) = 0` via marching squares
- Sliders for free parameters (`a·sin(b·x)`)
- Export the current view as PNG or SVG
