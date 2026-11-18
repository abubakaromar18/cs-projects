import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Viewport, MIN_SPAN } from '../src/viewport.js';
import { niceStep, ticks, formatTick } from '../src/ticks.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} !≈ ${b}`);
const vp = () => new Viewport({ xMin: -10, xMax: 10, yMin: -5, yMax: 5, width: 200, height: 100 });

test('world <-> screen round trip', () => {
  const v = vp();
  near(v.toScreenX(-10), 0);
  near(v.toScreenX(10), 200);
  near(v.toScreenY(5), 0);   // top of screen = yMax
  near(v.toScreenY(-5), 100);
  for (const x of [-7.3, 0, 4.2]) near(v.toWorldX(v.toScreenX(x)), x);
  for (const y of [-3.1, 0, 2.2]) near(v.toWorldY(v.toScreenY(y)), y);
});

test('rejects invalid bounds and is immutable', () => {
  assert.throws(() => new Viewport({ xMin: 1, xMax: 1 }), RangeError);
  const v = vp();
  assert.throws(() => { 'use strict'; v.xMin = 3; }, TypeError);
});

test('panning moves content with the drag', () => {
  // Dragging right by 20px (10% of width) should reveal content to the left.
  const v = vp().panByPixels(20, 10);
  near(v.xMin, -12);
  near(v.xMax, 8);
  // Dragging down by 10px (10% of height) reveals content above.
  near(v.yMin, -4);
  near(v.yMax, 6);
});

test('zoom keeps the point under the cursor fixed', () => {
  const v = vp();
  const sx = 150;
  const sy = 30;
  const before = [v.toWorldX(sx), v.toWorldY(sy)];
  const z = v.zoomAt(sx, sy, 0.5);
  near(z.xSpan, 10);
  near(z.ySpan, 5);
  near(z.toWorldX(sx), before[0]);
  near(z.toWorldY(sy), before[1]);
});

test('axis-only zoom and span clamping', () => {
  const z = vp().zoomAt(100, 50, 0.5, 1);
  near(z.xSpan, 10);
  near(z.ySpan, 10);
  const tiny = vp().zoomAt(100, 50, 1e-30);
  near(tiny.xSpan, MIN_SPAN, 1e-15);
});

test('resize keeps centre and scale', () => {
  const r = vp().resize(400, 100);
  near(r.xMin, -20);
  near(r.xMax, 20);
  near(r.yMin, -5);
  near(r.yMax, 5);
});

test('niceStep picks 1/2/5 x 10^n', () => {
  assert.equal(niceStep(10, 10), 1);
  assert.equal(niceStep(20, 10), 2);
  assert.equal(niceStep(50, 10), 5);
  near(niceStep(0.3, 6), 0.05);
  assert.equal(niceStep(9000, 10), 1000);
  assert.throws(() => niceStep(0), RangeError);
});

test('ticks are exact multiples of the step and include zero', () => {
  const { step, values } = ticks(-1, 1, 4);
  assert.equal(step, 0.5);
  assert.deepEqual(values, [-1, -0.5, 0, 0.5, 1]);
  const t = ticks(0.1, 0.35, 5);
  assert.equal(t.step, 0.05);
  for (const v of t.values) near(v / t.step, Math.round(v / t.step));
});

test('tick formatting', () => {
  assert.equal(formatTick(0, 1), '0');
  assert.equal(formatTick(3, 1), '3');
  assert.equal(formatTick(0.30000000000000004, 0.1), '0.3');
  assert.equal(formatTick(-2.5, 0.5), '-2.5');
  assert.equal(formatTick(2e7, 1e6), '2e+7');
  assert.equal(formatTick(0.00002, 0.00001), '2e-5');
});
