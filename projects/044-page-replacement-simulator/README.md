# 044 · Page Replacement Simulator

When physical memory is full and a process touches a page that isn't resident,
the OS must pick a victim to evict. This simulator runs the four classic
policies — **FIFO, LRU, Clock and OPT** — over any reference string, draws the
textbook trace grid, compares fault counts, sweeps frame counts, and finds
**Belady's anomaly** on its own. Pure Python, no dependencies.

## What it does

- `trace` — step-by-step grid (or one line per reference, with Clock's reference bits and hand).
- `compare` — all policies on one workload, with each one's gap to optimal.
- `sweep` — fault curve over a range of frame counts, as a table or ASCII bars; flags any anomaly.
- `belady` — shows the classic anomaly string, or randomly searches for a new one.
- Workloads: explicit strings, presets (`textbook`, `belady`), or generated `uniform`, `locality` (working-set phases) and `loop` (sequential scan).

## CS concepts

| Concept | Where |
|---|---|
| Demand paging, compulsory vs. capacity faults | `simulator.py` `simulate` |
| FIFO queue of load order | `policies.py` `FIFO` |
| LRU via last-use timestamps | `policies.py` `LRU` |
| Clock / second chance: reference bits and a sweeping hand | `policies.py` `Clock` |
| Belady's OPT (MIN), with next-use precomputed in one reverse pass | `policies.py` `OPT` |
| Strategy pattern: policies only choose a victim, the simulator owns frames | `Policy` base class |
| Belady's anomaly, stack algorithms and the inclusion property | `analysis.py` |
| Temporal locality and the working-set model | `refstrings.locality` |

**Why LRU and OPT never show the anomaly.** Both are *stack algorithms*: at
every moment, the pages held with *k* frames are a subset of those held with
*k+1*. So adding a frame can never turn a hit into a fault.
`analysis.is_stack_inclusive` checks this directly. FIFO and Clock lack the
property, which is why the sweep catches both of them on the `belady` preset.

## Build, run, test

```bash
make dev        # pip install -e '.[dev]'  (Python 3.10+)
make test       # 41 tests
make demo       # textbook trace + comparison + Belady demo

pagesim compare -f 3                       # after install
make run ARGS="sweep --chart --preset belady -F 1-5"
```

Without installing: `PYTHONPATH=src python3 -m page_replacement <command>`.

## Example output

```text
$ pagesim trace -a lru -f 3
ref    7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1
f0     7 . . 2 . . . 4 . . 0 . . 1 . . . . . .
f1     - 0 . . . . . . . 3 . . . . . 0 . . . .
f2     - . 1 . . 3 . . 2 . . . . . . . . 7 . .
fault  * * * *   *   * * * *     *   *   *
LRU: 12 faults, 8 hits (40% hit ratio) with 3 frames

$ pagesim compare -f 4 --gen locality -n 1000 -p 20 --seed 7
algorithm   faults    hits   hit %   vs OPT
-------------------------------------------
opt            219     781   78.1%        =
lru            302     698   69.8%      +83
clock          322     678   67.8%     +103
fifo           330     670   67.0%     +111

$ pagesim belady
refs: 1 2 3 4 1 2 5 1 2 3 4 5
FIFO: 3 frames -> 9 faults, but 4 frames -> 10 faults (Belady's anomaly)
```

`.` in the grid means the frame didn't change; `*` marks a fault.

## Testing approach

- Known textbook answers (Silberschatz string: FIFO 15, LRU 12, OPT 9 with 3 frames).
- Each policy is checked against a separately written reference model on 300 random strings.
- OPT is checked against an exhaustive search over every eviction choice for all strings of length 7 over 4 pages.
- Properties: OPT never loses, compulsory-fault lower bound, LRU's worst case on loops, the inclusion property.

## Possible extensions

- More policies: LFU, MRU, NRU, Random, Enhanced Clock (reference + dirty bits), WSClock, ARC.
- Dirty pages and write-back cost, so the trace counts disk writes as well as faults.
- Multiple processes with global vs. local replacement, and thrashing detection.
- Load real traces (e.g. from `valgrind --tool=lackey`).
- An HTML or matplotlib plot of the sweep curves.
