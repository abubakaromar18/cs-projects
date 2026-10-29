# 018 · Logic Gate Simulator

A drag-and-drop digital logic simulator that runs in the browser, written in TypeScript with no runtime dependencies. You drop gates onto a board, wire output pins to input pins, flip switches and watch the signals light up. A live truth table shows the circuit's behaviour, and the app writes out its sum-of-products expression. Built-in examples go from a half adder to a 4-bit ripple-carry adder and a NOR-based SR latch.

**Level:** Starter · **Area:** Embedded & Emulation

## Features

- **Ten primitives:** INPUT switch, OUTPUT lamp, BUFFER, NOT, AND, OR, NAND, NOR, XOR and XNOR.
- **Drag from the palette** onto the board, drag gates to move them (snapped to the grid), and drag from an output pin to an input pin to wire them up.
- **Live simulation:** wires and lamps glow when they carry a HIGH signal.
- **Truth table panel:** lists every input combination, with the current row highlighted and the canonical sum-of-products for each output (A'B + AB').
- **Feedback loops work.** Latches keep their memory, and oscillating circuits (a NOT gate wired to itself) are flagged as unstable instead of freezing the page.
- **Examples:** half adder, full adder, 4-bit ripple-carry adder, SR latch and NAND universality.
- **Export and import** circuits as JSON. The current board is autosaved in `localStorage`.

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Boolean algebra and logic gates.** Each gate is a pure function `boolean[] → boolean`, stored in a declarative table, so the engine has no `switch` over gate kinds. | `src/core/gates.ts` |
| **Circuits as directed graphs.** Nodes are gates and edges are wires. Every input pin has at most one driver, fan-out is unlimited, and an undriven pin reads LOW. | `src/core/circuit.ts` |
| **Topological sort (Kahn's algorithm).** Combinational circuits are evaluated in one O(V+E) pass, so each gate is computed after all of its inputs. | `Circuit.topologicalOrder` |
| **Cycle detection.** If Kahn's algorithm can't emit every node, the circuit has feedback and is therefore sequential. | `Circuit.simulate` |
| **Fixed-point iteration (Gauss–Seidel).** Feedback circuits are swept until nothing changes. Values persist between runs, and that persistence is what gives a latch memory. A sweep cap detects oscillation. | `Circuit.simulate` |
| **Binary addition in hardware.** Half adder, then full adder, then an n-bit ripple-carry adder, where the carry chain explains O(n) adder delay. | `src/core/library.ts` |
| **Sequential logic.** A cross-coupled NOR SR latch shows set, reset, hold and the forbidden state. | `srLatch()` |
| **Functional completeness.** NOT, AND and OR are built from NAND gates only. | `nandUniversality()` |
| **Truth-table enumeration and DNF synthesis.** The app counts through 2ⁿ inputs and ORs together one minterm per true row. | `src/core/analysis.ts` |
| **Validated serialization.** Untrusted JSON is checked field by field before it reaches the engine. | `src/core/serialize.ts` |
| **Model–view separation.** The core is DOM-free and fully tested in Node. The UI re-renders the SVG from the model on each change. | `src/ui/` |

## Project structure

```
018-logic-gate-simulator/
├── index.html            # toolbar, palette, SVG board, truth-table panel
├── styles.css            # light/dark theme
├── src/
│   ├── core/
│   │   ├── gates.ts      # gate specs (arity, evaluate, symbol)
│   │   ├── circuit.ts    # graph model + simulation engine
│   │   ├── analysis.ts   # truth tables, sum-of-products
│   │   ├── library.ts    # adders, latch, NAND universality
│   │   └── serialize.ts  # JSON save/load with validation
│   └── ui/
│       ├── geometry.ts   # pin positions, Bézier wire paths, grid snap
│       └── app.ts        # SVG editor: drag, wire, toggle, render
└── test/                 # node:test suites (compiled by tsc)
```

## Build and run

Requires Node 18 or newer.

```bash
npm install        # installs TypeScript (dev-only)
npm start          # compiles to dist/ and serves http://localhost:5173
```

Or build once with `npm run build` and serve the folder any way you like (`python3 -m http.server 5173`). ES modules need HTTP, so opening `index.html` as a `file://` URL won't work.

## Test

```bash
npm test           # compiles src/core + tests and runs node --test
npm run typecheck  # strict type-check of the whole app, including the DOM code
```

The 26 tests cover every gate's truth table, topological ordering and cycle detection, wire replacement and fan-out, and error handling. They also check the full adder exhaustively, run all 512 cases of the 4-bit adder, test SR latch set/hold/reset, the NAND-only circuits, sum-of-products output, JSON round-trips of every example and rejection of malformed files.

```
# tests 26
# pass 26
# fail 0
```

## Example usage

Load **Half adder** and the truth-table panel shows:

| A | B | C | S |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 0 | 1 |
| 1 | 0 | 0 | 1 |
| 1 | 1 | 1 | 0 |

```
C = AB
S = A'B + AB'
```

The core also works headless from code:

```ts
import { rippleCarryAdder } from "./src/core/library.js";
import { bitsToNumber } from "./src/core/analysis.js";

const adder = rippleCarryAdder(4);
// 11 + 6
[1, 1, 0, 1].forEach((b, i) => adder.setInput(`A${i}`, !!b)); // 11 = 1011₂ (LSB first)
[0, 1, 1, 0].forEach((b, i) => adder.setInput(`B${i}`, !!b)); //  6 = 0110₂
adder.simulate();
const sum = [0, 1, 2, 3].map((i) => adder.value(`S${i}`)).concat(adder.value("Cout"));
console.log(bitsToNumber(sum)); // 17
```

Status bar for the SR latch after switching S on: `2 gates · 6 wires · sequential (has feedback) · settled in 2 sweeps`

## Possible extensions

- **Clock source and D flip-flop:** step the clock edge by edge to build counters and shift registers.
- **Propagation delay:** switch to event-driven simulation with per-gate delays so glitches and the ripple-carry critical path become visible.
- **Sub-circuits:** save a selection as a reusable black-box component, such as a "FullAdder" chip.
- **Karnaugh maps and Quine–McCluskey** to turn the sum-of-products into a minimal expression.
- **Multi-input gates** (3- and 4-input AND/OR) and multi-bit buses with hex displays.
- **Undo/redo** using the command pattern over editor actions.
