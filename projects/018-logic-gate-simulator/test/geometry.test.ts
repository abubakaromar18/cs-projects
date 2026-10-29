import { test } from "node:test";
import assert from "node:assert/strict";
import { gateSize, inputPinPos, outputPinPos, snap, wirePath } from "../src/ui/geometry.js";

test("input pins are evenly spaced down the left edge", () => {
  const { h } = gateSize("AND");
  const p0 = inputPinPos("AND", 100, 50, 0);
  const p1 = inputPinPos("AND", 100, 50, 1);
  assert.equal(p0.x, 100);
  assert.ok(Math.abs(p1.y - p0.y - h / 3) < 1e-9);
  assert.equal(inputPinPos("NOT", 0, 0, 0).y, gateSize("NOT").h / 2);
});

test("output pin sits mid-way down the right edge", () => {
  const { w, h } = gateSize("XOR");
  assert.deepEqual(outputPinPos("XOR", 10, 20), { x: 10 + w, y: 20 + h / 2 });
});

test("wire path starts and ends on the pins", () => {
  const d = wirePath({ x: 0, y: 0 }, { x: 200, y: 50 });
  assert.match(d, /^M 0 0 C .* 200 50$/);
});

test("snap rounds to the grid", () => {
  assert.equal(snap(14), 10);
  assert.equal(snap(15), 20);
  assert.equal(snap(40), 40);
});
