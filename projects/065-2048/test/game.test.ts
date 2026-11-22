import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { Game, type Rng } from "../src/game.js";

/** Deterministic RNG cycling through fixed values. */
function seq(...values: number[]): Rng {
  let i = 0;
  return () => values[i++ % values.length]!;
}

/** Game with spawning that always picks the first empty cell and a 2. */
const opts = () => ({ rng: seq(0, 0.5) });

/** Slide a single row left and return the resulting row (ignoring spawns). */
function slideRow(row: number[]): number[] {
  const g = Game.fromGrid([row, [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], { rng: seq(0.99, 0.5) });
  g.move("left");
  return g.toGrid()[0]!;
}

describe("merge rules", () => {
  const cases: [number[], number[]][] = [
    [[2, 2, 0, 0], [4, 0, 0, 0]],
    [[2, 0, 2, 0], [4, 0, 0, 0]],
    [[2, 2, 2, 2], [4, 4, 0, 0]],
    [[2, 2, 2, 0], [4, 2, 0, 0]],
    [[4, 2, 2, 0], [4, 4, 0, 0]], // no chain merge into 8
    [[2, 2, 4, 4], [4, 8, 0, 0]],
    [[4, 4, 4, 0], [8, 4, 0, 0]],
    [[0, 0, 0, 2], [2, 0, 0, 0]],
    [[2, 4, 8, 16], [2, 4, 8, 16]],
    [[8, 0, 8, 8], [16, 8, 0, 0]],
  ];
  for (const [input, expected] of cases) {
    test(`${JSON.stringify(input)} ← ${JSON.stringify(expected)}`, () => {
      assert.deepEqual(slideRow(input), expected);
    });
  }
});

describe("directions", () => {
  const start = [
    [2, 0, 0, 2],
    [0, 4, 0, 0],
    [0, 4, 0, 0],
    [2, 0, 0, 0],
  ];
  // RNG 0.99 spawns into the last empty cell; we only check non-spawn cells.
  test("right", () => {
    const g = Game.fromGrid(start, { rng: seq(0, 0.5) });
    const r = g.move("right");
    const grid = g.toGrid();
    assert.equal(grid[0]![3], 4);
    assert.equal(grid[1]![3], 4);
    assert.equal(grid[2]![3], 4);
    assert.equal(grid[3]![3], 2);
    assert.equal(r.scoreGained, 4);
  });
  test("up merges columns", () => {
    const g = Game.fromGrid(start, { rng: seq(0.99, 0.5) });
    g.move("up");
    const grid = g.toGrid();
    assert.deepEqual(grid[0], [4, 8, 0, 2]);
    assert.deepEqual(grid[1]!.slice(0, 3), [0, 0, 0]);
  });
  test("down", () => {
    const g = Game.fromGrid(start, { rng: seq(0, 0.5) });
    g.move("down");
    assert.deepEqual(g.toGrid()[3], [4, 8, 0, 2]);
  });
});

describe("moves and scoring", () => {
  test("no-op move does not spawn or record history", () => {
    const g = Game.fromGrid([[2, 4, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], opts());
    const r = g.move("left");
    assert.equal(r.moved, false);
    assert.equal(r.spawned, null);
    assert.equal(g.getTiles().length, 2);
    assert.equal(g.canUndo, false);
  });

  test("score accumulates merged values", () => {
    const g = Game.fromGrid([[2, 2, 4, 4], [8, 8, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], { rng: seq(0.99, 0.5) });
    const r = g.move("left");
    assert.equal(r.scoreGained, 4 + 8 + 16);
    assert.equal(g.score, 28);
  });

  test("valid move spawns exactly one tile", () => {
    const g = Game.fromGrid([[0, 0, 0, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], opts());
    const r = g.move("left");
    assert.ok(r.spawned);
    assert.equal(g.getTiles().length, 2);
  });

  test("spawn respects fourProbability", () => {
    const g = new Game({ rng: seq(0, 0.05), fourProbability: 0.1 }, 1);
    assert.equal(g.getTiles()[0]!.value, 4);
    const h = new Game({ rng: seq(0, 0.5), fourProbability: 0.1 }, 1);
    assert.equal(h.getTiles()[0]!.value, 2);
  });

  test("new game starts with two tiles", () => {
    const g = new Game();
    assert.equal(g.getTiles().length, 2);
    assert.equal(g.score, 0);
  });
});

describe("animation metadata", () => {
  test("moves and merges describe tile identities", () => {
    const g = Game.fromGrid([[0, 2, 0, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], { rng: seq(0.99, 0.5) });
    const [a, b] = g.getTiles();
    const r = g.move("left");
    assert.equal(r.merges.length, 1);
    const merge = r.merges[0]!;
    assert.deepEqual(merge.sources, [a!.id, b!.id]);
    assert.deepEqual(merge.at, { row: 0, col: 0 });
    assert.equal(merge.value, 4);
    // Both sources slide to (0,0).
    for (const id of [a!.id, b!.id]) {
      const m = r.moves.find((x) => x.id === id);
      assert.deepEqual(m?.to, { row: 0, col: 0 });
    }
    // The merged tile exists in the new state with a fresh id; sources are gone.
    const ids = g.getTiles().map((t) => t.id);
    assert.ok(ids.includes(merge.id));
    assert.ok(!ids.includes(a!.id) && !ids.includes(b!.id));
  });

  test("tile ids are unique across moves", () => {
    const g = new Game({ rng: seq(0.13, 0.7, 0.42, 0.05, 0.88) });
    const dirs = ["left", "up", "right", "down"] as const;
    for (let i = 0; i < 200 && !g.over; i++) {
      g.move(dirs[i % 4]!);
      const ids = g.getTiles().map((t) => t.id);
      assert.equal(new Set(ids).size, ids.length);
    }
  });
});

describe("win / lose", () => {
  test("reaching the target sets justWon once", () => {
    const g = Game.fromGrid([[1024, 1024, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], opts());
    const r = g.move("left");
    assert.equal(r.justWon, true);
    assert.equal(g.won, true);
    assert.equal(g.paused, true);
    g.continueAfterWin();
    assert.equal(g.paused, false);
  });

  test("custom target", () => {
    const g = Game.fromGrid([[8, 8, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], { ...opts(), target: 16 });
    assert.equal(g.move("left").justWon, true);
  });

  test("full board with no pairs is game over", () => {
    const g = Game.fromGrid([
      [2, 4, 2, 4],
      [4, 2, 4, 2],
      [2, 4, 2, 4],
      [4, 2, 4, 2],
    ]);
    assert.equal(g.canMove(), false);
    assert.equal(g.over, true);
  });

  test("full board with a vertical pair is not over", () => {
    const g = Game.fromGrid([
      [2, 4, 2, 4],
      [2, 8, 4, 2],
      [8, 4, 2, 4],
      [4, 2, 4, 2],
    ]);
    assert.equal(g.over, false);
  });
});

describe("undo and snapshots", () => {
  test("undo restores board and score", () => {
    const g = Game.fromGrid([[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], opts());
    const before = g.toGrid();
    g.move("left");
    assert.equal(g.score, 4);
    assert.equal(g.undo(), true);
    assert.deepEqual(g.toGrid(), before);
    assert.equal(g.score, 0);
    assert.equal(g.undo(), false, "only one level of undo");
  });

  test("snapshot round-trip", () => {
    const g = new Game({ rng: seq(0.3, 0.6, 0.9) });
    g.move("left");
    g.move("up");
    const copy = Game.fromSnapshot(JSON.parse(JSON.stringify(g.snapshot())));
    assert.deepEqual(copy.toGrid(), g.toGrid());
    assert.equal(copy.score, g.score);
  });

  test("snapshots are isolated from later mutation", () => {
    const g = Game.fromGrid([[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], opts());
    const s = g.snapshot();
    g.move("left");
    assert.equal(s.tiles.length, 2);
  });
});

describe("validation", () => {
  test("rejects bad sizes", () => {
    assert.throws(() => new Game({ size: 1 }), RangeError);
    assert.throws(() => Game.fromGrid([[2, 0], [0]]), RangeError);
  });
  test("supports other board sizes", () => {
    const g = Game.fromGrid([[2, 2, 2, 2, 2], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]], { rng: seq(0.99, 0.5) });
    g.move("left");
    assert.deepEqual(g.toGrid()[0], [4, 4, 2, 0, 0]);
  });
});
