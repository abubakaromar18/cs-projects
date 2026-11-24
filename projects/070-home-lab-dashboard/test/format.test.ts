import { test } from "node:test";
import assert from "node:assert/strict";
import {
  formatLatency, formatUptime, groupServices, matchesFilter, overallHealth, relativeTime, safeHref, sparkline,
} from "../src/client/format.js";
import type { CheckResult, Health, ServiceStatus } from "../src/shared/types.js";

const status = (name: string, group: string, extra: Partial<ServiceStatus> = {}): ServiceStatus => ({
  id: name, name, group, url: `http://${name.toLowerCase()}.lan`, checkType: "http",
  current: { health: "up", detail: "", checkedAt: 0 }, history: [], uptimePercent: null, ...extra,
});
const res = (health: Health, latencyMs?: number): CheckResult => ({ health, latencyMs, detail: "", checkedAt: 0 });

test("relativeTime", () => {
  const now = 1_000_000_000;
  assert.equal(relativeTime(0, now), "never");
  assert.equal(relativeTime(now - 2000, now), "just now");
  assert.equal(relativeTime(now - 42_000, now), "42s ago");
  assert.equal(relativeTime(now - 5 * 60_000, now), "5m ago");
  assert.equal(relativeTime(now - 3 * 3_600_000, now), "3h ago");
  assert.equal(relativeTime(now - 50 * 3_600_000, now), "2d ago");
});

test("latency and uptime formatting", () => {
  assert.equal(formatLatency(undefined), "–");
  assert.equal(formatLatency(87), "87 ms");
  assert.equal(formatLatency(1234), "1.23 s");
  assert.equal(formatLatency(12_345), "12.3 s");
  assert.equal(formatUptime(null), "–");
  assert.equal(formatUptime(100), "100%");
  assert.equal(formatUptime(99.5), "99.5%");
  assert.equal(formatUptime(0), "0%");
});

test("groupServices keeps config order", () => {
  const g = groupServices([status("A", "Media"), status("B", "Infra"), status("C", "Media")]);
  assert.deepEqual([...g.keys()], ["Media", "Infra"]);
  assert.deepEqual(g.get("Media")!.map((s) => s.name), ["A", "C"]);
});

test("matchesFilter requires every word", () => {
  const s = status("Jellyfin", "Media", { description: "Movies & TV" });
  assert.ok(matchesFilter(s, ""));
  assert.ok(matchesFilter(s, "jelly"));
  assert.ok(matchesFilter(s, "media movies"));
  assert.ok(!matchesFilter(s, "media plex"));
});

test("safeHref allows web/lab schemes only", () => {
  assert.equal(safeHref("http://x.lan/"), "http://x.lan/");
  assert.equal(safeHref("ssh://user@box"), "ssh://user@box");
  assert.equal(safeHref("javascript:alert(1)"), undefined);
  assert.equal(safeHref("not a url"), undefined);
});

test("overallHealth picks the worst state", () => {
  assert.equal(overallHealth({ up: 3, degraded: 1, down: 1, unknown: 0 }), "down");
  assert.equal(overallHealth({ up: 3, degraded: 1, down: 0, unknown: 0 }), "degraded");
  assert.equal(overallHealth({ up: 3, degraded: 0, down: 0, unknown: 2 }), "up");
  assert.equal(overallHealth({ up: 0, degraded: 0, down: 0, unknown: 2 }), "unknown");
});

test("sparkline scales to max latency, right-aligns, and maxes out down bars", () => {
  const bars = sparkline([res("up", 50), res("up", 100), res("down"), res("unknown")], 6, 20);
  assert.deepEqual(bars.map((b) => b.x), [2, 3, 4, 5]);
  assert.deepEqual(bars.map((b) => b.height), [10, 20, 20, 1]);
  assert.equal(sparkline(Array.from({ length: 10 }, () => res("up", 1)), 4, 10).length, 4);
});
