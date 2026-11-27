import { test } from "node:test";
import assert from "node:assert/strict";
import { buildHeatmap, heatColor, mergeKeyStats, weakestKeys } from "../src/core/heatmap.js";
import { keyIdFor, needsShift, QWERTY_ROWS } from "../src/core/keyboard.js";
import type { KeyStats } from "../src/core/session.js";

const stat = (attempts: number, misses: number, lat = 0, n = 0) =>
  ({ attempts, misses, latencyTotal: lat, latencyCount: n });

test("keyboard maps shifted chars to their physical key", () => {
  assert.equal(keyIdFor("A"), "a");
  assert.equal(keyIdFor("?"), "/");
  assert.equal(keyIdFor(" "), "space");
  assert.equal(needsShift("A"), true);
  assert.equal(needsShift("a"), false);
  assert.equal(keyIdFor("é"), undefined);
});

test("heatmap covers every key; keys without data have null intensity", () => {
  const rows = buildHeatmap({}, { mode: "errors" });
  assert.equal(rows.length, QWERTY_ROWS.length);
  rows.forEach((r, i) => assert.equal(r.length, QWERTY_ROWS[i]!.length));
  assert.ok(rows.flat().every((c) => c.intensity === null && c.color === null));
});

test("error intensity is smoothed by the prior and clamped", () => {
  const stats: KeyStats = { a: stat(1, 1), s: stat(100, 50), d: stat(20, 0) };
  const cells = new Map(buildHeatmap(stats, { mode: "errors" }).flat().map((c) => [c.key.id, c]));
  // a: 1 / (1+2) = 0.333 → /0.25 → clamped to 1
  assert.equal(cells.get("a")!.intensity, 1);
  assert.equal(cells.get("a")!.errorRate, 1);
  assert.equal(cells.get("d")!.intensity, 0);
  const s = cells.get("s")!.intensity!;
  assert.equal(s, 1);
  const mild = buildHeatmap({ f: stat(18, 1) }, { mode: "errors" }).flat().find((c) => c.key.id === "f")!;
  assert.ok(Math.abs(mild.intensity! - 0.2) < 1e-9); // 1/20 / 0.25
});

test("latency mode normalises between fastest and slowest key", () => {
  const stats: KeyStats = { a: stat(5, 0, 500, 5), s: stat(5, 0, 1500, 5), d: stat(5, 0, 1000, 5) };
  const cells = new Map(buildHeatmap(stats, { mode: "latency" }).flat().map((c) => [c.key.id, c]));
  assert.equal(cells.get("a")!.intensity, 0);
  assert.equal(cells.get("s")!.intensity, 1);
  assert.equal(cells.get("d")!.intensity, 0.5);
  assert.equal(cells.get("d")!.avgLatency, 200);
});

test("weakestKeys ranks letters by smoothed error rate, requires min samples", () => {
  const stats: KeyStats = {
    a: stat(10, 0, 1000, 10), s: stat(10, 4), d: stat(10, 2), q: stat(1, 1), ";": stat(10, 9),
  };
  assert.deepEqual(weakestKeys(stats, 2), ["s", "d"]);
  assert.deepEqual(weakestKeys(stats, 5), ["s", "d", "a"]);
});

test("mergeKeyStats sums fields without mutating inputs", () => {
  const a: KeyStats = { x: stat(1, 1, 10, 1) };
  const b: KeyStats = { x: stat(2, 0, 20, 2), y: stat(1, 0) };
  const m = mergeKeyStats(a, b);
  assert.deepEqual(m.x, stat(3, 1, 30, 3));
  assert.deepEqual(m.y, stat(1, 0));
  assert.deepEqual(a.x, stat(1, 1, 10, 1));
});

test("heatColor ramps green → red", () => {
  assert.equal(heatColor(0), "hsl(120 75% 50%)");
  assert.equal(heatColor(0.5), "hsl(60 75% 50%)");
  assert.equal(heatColor(1), "hsl(0 75% 50%)");
  assert.equal(heatColor(7), "hsl(0 75% 50%)");
});
