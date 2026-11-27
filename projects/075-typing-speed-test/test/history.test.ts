import { test } from "node:test";
import assert from "node:assert/strict";
import { History, type KVStore, type RunRecord } from "../src/core/history.js";

class MemStore implements KVStore {
  m = new Map<string, string>();
  getItem(k: string) { return this.m.get(k) ?? null; }
  setItem(k: string, v: string) { this.m.set(k, v); }
}

const run = (netWpm: number, mode = "words-25"): RunRecord => ({
  at: "2026-01-01T00:00:00Z", mode, netWpm, rawWpm: netWpm + 5, accuracy: 95, consistency: 80, durationMs: 10_000,
});

test("tracks personal bests per mode and persists across instances", () => {
  const store = new MemStore();
  const h = new History(store);
  assert.equal(h.add(run(50), {}), true);
  assert.equal(h.add(run(40), {}), false);
  assert.equal(h.add(run(30, "time-30"), {}), true, "first run of a new mode is a PB");
  assert.equal(h.add(run(60), { a: { attempts: 2, misses: 1, latencyTotal: 0, latencyCount: 0 } }), true);

  const h2 = new History(store);
  assert.equal(h2.runs.length, 4);
  assert.equal(h2.best("words-25")!.netWpm, 60);
  assert.equal(h2.recentAverage(2), 45);
  assert.equal(h2.lifetimeKeyStats.a!.misses, 1);
});

test("corrupted or wrong-version data is ignored", () => {
  for (const bad of ["{not json", JSON.stringify({ version: 99 }), JSON.stringify({ version: 1, runs: "x" })]) {
    const store = new MemStore();
    store.m.set("typing-speed-test:v1", bad);
    const h = new History(store);
    assert.equal(h.runs.length, 0);
  }
});

test("works with no storage and with throwing storage", () => {
  const none = new History(null);
  none.add(run(10), {});
  assert.equal(none.runs.length, 1);

  const throwing: KVStore = {
    getItem() { throw new Error("SecurityError"); },
    setItem() { throw new Error("QuotaExceeded"); },
  };
  const h = new History(throwing);
  assert.doesNotThrow(() => h.add(run(10), {}));
  assert.equal(h.recentAverage(), 10);
});

test("clear() wipes runs and key stats", () => {
  const h = new History(new MemStore());
  h.add(run(10), { a: { attempts: 1, misses: 0, latencyTotal: 0, latencyCount: 0 } });
  h.clear();
  assert.equal(h.runs.length, 0);
  assert.deepEqual(h.lifetimeKeyStats, {});
  assert.equal(h.recentAverage(), null);
});
