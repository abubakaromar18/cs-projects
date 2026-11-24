import { test } from "node:test";
import assert from "node:assert/strict";
import { Monitor, RingBuffer, mapWithConcurrency, uptimePercent } from "../src/server/monitor.js";
import type { CheckResult, DashboardConfig, Health, ServiceConfig } from "../src/shared/types.js";

const r = (health: Health, latencyMs?: number): CheckResult => ({ health, latencyMs, detail: health, checkedAt: 1 });
const svc = (id: string): ServiceConfig => ({ id, name: id, url: `http://${id}`, group: "g", check: { type: "http", timeoutMs: 1, slowMs: 1 } });
const config = (ids: string[], historySize = 3): DashboardConfig => ({ title: "T", intervalSeconds: 60, historySize, services: ids.map(svc) });

test("RingBuffer keeps the newest N in order", () => {
  const b = new RingBuffer<number>(3);
  assert.deepEqual(b.toArray(), []);
  assert.equal(b.last(), undefined);
  [1, 2, 3, 4, 5].forEach((n) => b.push(n));
  assert.deepEqual(b.toArray(), [3, 4, 5]);
  assert.equal(b.size, 3);
  assert.equal(b.last(), 5);
  assert.throws(() => new RingBuffer(0), RangeError);
});

test("uptimePercent ignores unknown samples and counts degraded as up", () => {
  assert.equal(uptimePercent([]), null);
  assert.equal(uptimePercent([r("unknown")]), null);
  assert.equal(uptimePercent([r("up"), r("degraded"), r("down"), r("unknown")]), 66.7);
  assert.equal(uptimePercent([r("up"), r("up")]), 100);
});

test("mapWithConcurrency respects the limit and preserves order", async () => {
  let inFlight = 0, peak = 0;
  const out = await mapWithConcurrency([5, 1, 4, 2, 3], 2, async (n) => {
    inFlight++; peak = Math.max(peak, inFlight);
    await new Promise((res) => setTimeout(res, n * 3));
    inFlight--;
    return n * 10;
  });
  assert.deepEqual(out, [50, 10, 40, 20, 30]);
  assert.equal(peak, 2);
});

test("snapshot before any check reports unknown", () => {
  const snap = new Monitor(config(["a", "b"]), { clock: () => 42 }).snapshot();
  assert.equal(snap.generatedAt, 42);
  assert.deepEqual(snap.summary, { up: 0, degraded: 0, down: 0, unknown: 2 });
  assert.equal(snap.services[0].current.detail, "not checked yet");
});

test("rounds accumulate bounded history, summary and uptime", async () => {
  const script: Record<string, Health[]> = { a: ["up", "down", "up", "up"], b: ["down", "down", "down", "degraded"] };
  let round = 0;
  const m = new Monitor(config(["a", "b"], 3), { checker: async (s) => r(script[s.id][round], 10) });
  for (round = 0; round < 4; round++) await m.checkAll();
  const snap = m.snapshot();
  assert.equal(m.completedRounds, 4);
  const [a, b] = snap.services;
  assert.deepEqual(a.history.map((h) => h.health), ["down", "up", "up"]);
  assert.equal(a.uptimePercent, 66.7);
  assert.equal(b.current.health, "degraded");
  assert.deepEqual(snap.summary, { up: 1, degraded: 1, down: 0, unknown: 0 });
});

test("concurrent checkAll calls share one round; throwing checker becomes down", async () => {
  let calls = 0;
  const m = new Monitor(config(["a"]), {
    checker: async () => { calls++; await new Promise((res) => setTimeout(res, 10)); throw new Error("kaboom"); },
  });
  await Promise.all([m.checkAll(), m.checkAll(), m.checkAll()]);
  assert.equal(calls, 1);
  const cur = m.snapshot().services[0].current;
  assert.equal(cur.health, "down");
  assert.match(cur.detail, /kaboom/);
});
