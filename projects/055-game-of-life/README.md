# Game of Life: Process per Cell

Conway's Game of Life in Elixir, where **every cell is its own BEAM process**. A 40×20 board is 800 GenServers. They share no memory and have no global view. They only talk to their eight neighbours by message passing. A coordinator process runs each generation as a barrier: it ticks every cell and waits for all of them to report back.

A pure, functional `Grid` implementation sits next to it. The test suite checks that the two always agree.

```
$ mix life --file examples/gosper-gun.txt --gens 30 --verify
gen 30  pop 41
······································
·························█············
·······················█·█············
·············██······██············██·
············█···█····██············██·
·██········█·····█···██···············
·██········█···█·██····█·█············
···········█·····█·······█············
············█···█·····················
·············██·······················
························█·············     ← first glider leaving the gun
·························██···········
························██············
...
836 cell processes · 30 generations · final population 41 · 222.4 ms · verified ✓
```

## CS concepts demonstrated

- **Actor model.** Each cell is an isolated GenServer with private state. All coordination is asynchronous message passing (`GenServer.cast`). Nothing is shared and nothing is locked.
- **Barrier synchronisation.** `Board.step/1` broadcasts `{:tick, gen}` and replies only after all `width × height` cells send `{:cell_done, …}`. No cell can get more than one generation ahead of any other.
- **Handling out-of-order messages.** A neighbour's gossip for generation *g* can arrive before a cell's own tick for *g*. Each cell buffers gossip in a per-generation inbox (`%{gen => {heard, live}}`) and only commits once it has been ticked *and* heard from every neighbour. Generation tags prevent stale or early messages from being counted in the wrong generation.
- **Deferred GenServer replies.** The board stores the caller's `from` and answers later with `GenServer.reply/2`, so it never blocks inside a callback while it waits for cells.
- **Process registry and naming.** Cells register as `{board_ref, {x, y}}` in a partitioned `Registry`. The per-board `make_ref()` namespace lets many boards run concurrently. The tests run 8 at once.
- **Supervision trees.** Each board owns a `DynamicSupervisor` of cells. Stopping the board takes every cell down with it.
- **Functional reference model.** `Grid.step/1` is a pure function over a sparse `MapSet`. It counts neighbours by scattering +1 from each live cell into a frequency map, so it runs in O(population) instead of O(area).
- **Topology.** Bounded plane vs. torus (`wrap: true`). On tiny tori (1×N, 2×2) the same neighbour is adjacent more than once, and the self-adjacency counts with multiplicity. Both implementations handle this the same way, and it is tested.
- **Differential testing.** Random soups (seeded, bounded and toroidal) are stepped on both implementations and compared generation by generation.

## Layout

```
lib/
  game_of_life.ex              facade: centered/4, simulate/2
  game_of_life/application.ex  starts the cell Registry
  game_of_life/grid.ex         pure reference implementation (parse, render, step)
  game_of_life/cell.ex         one process per cell: the tick/gossip/commit protocol
  game_of_life/board.ex        coordinator: spawns cells, runs the generation barrier
  game_of_life/patterns.ex     glider, LWSS, pulsar, beacon, R-pentomino, acorn, …
  mix/tasks/life.ex            `mix life` terminal runner
examples/gosper-gun.txt        Gosper glider gun as a text pattern
test/                          ExUnit: rules, patterns, process board vs. reference
```

## The per-cell protocol

```
Board ──{:tick, g}──────────────▶ Cell(x,y)
Cell  ──{:neighbor, g, alive?}──▶ each of its neighbours
Cell  ◀─{:neighbor, g, alive?}── each of its neighbours   (buffered by g)
        heard all N?  → next = rule(alive, live_count)
Cell  ──{:cell_done, ref, g, pos, next}──▶ Board
Board: pending -= 1; at 0 → GenServer.reply(caller, new_grid)
```

## Build, run, test

Requires Elixir ≥ 1.14 (tested with Elixir 1.14 / OTP 24). The project has no dependencies.

```bash
mix test                 # 25 tests + 2 doctests
mix life --list          # built-in patterns
mix life --pattern glider --wrap --gens 40
mix life --pattern pulsar --width 17 --height 17 --gens 6
mix life --random --seed 1 --width 60 --height 24 --wrap --gens 200 --delay 60   # animated
mix life --file examples/gosper-gun.txt --gens 60 --verify
```

`make test`, `make run`, `make demo` and `make gun` are shortcuts.

Options: `--pattern`, `--file`, `--random`, `--density`, `--seed`, `--width`, `--height`, `--gens`, `--wrap`, `--delay MS` (redraws in place), and `--verify`, which checks every generation against `Grid.step/1`.

From `iex -S mix`:

```elixir
{:ok, g} = GameOfLife.centered("r-pentomino", 40, 20, wrap: true)
{:ok, b} = GameOfLife.Board.start_link(g)
GameOfLife.Board.process_count(b)          #=> 800
GameOfLife.Board.run(b, 50) |> GameOfLife.Grid.to_string() |> IO.puts()
```

## Is process-per-cell fast?

No, and that is the point of the experiment. Every generation sends about 8·N messages, while the pure version only touches live cells. On a 40×20 torus, 50 generations take about 0.3 s with processes and a few milliseconds with `Grid.step/1`. What you get in exchange is a model where cells really are independent, the work spreads across all schedulers automatically, and the same protocol would work if the cells were spread over several nodes.

## Possible extensions

- **Distribution.** Place regions of cells on different nodes (`Node.spawn`, `:global` or `:pg`) and watch the same protocol run over the network.
- **Fault tolerance.** Make cells `:transient`, checkpoint their state in the board, and restore a crashed cell mid-generation.
- **Lock-free asynchronous Life.** Drop the global barrier. Let each cell advance as soon as its neighbours have reached its generation (a local barrier), keeping a short history so slower neighbours can still be answered.
- **Region actors.** Use one process per 8×8 tile instead of per cell and compare message counts and throughput.
- **Other rules.** Support HighLife (B36/S23), Seeds (B2/S), or arbitrary `B…/S…` rule strings.
- **RLE import.** Parse the standard Run Length Encoded pattern format from LifeWiki.
- **LiveView front end.** Stream generations to a browser.
