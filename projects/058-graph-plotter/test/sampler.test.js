import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sample, pointCount } from '../src/sampler.js';
import { compile } from '../src/compiler.js';
import { Viewport } from '../src/viewport.js';

const view = new Viewport({ xMin: -10, xMax: 10, yMin: -10, yMax: 10, width: 400, height: 400 });

const isSorted = (segments) => {
  const xs = segments.flat().map(([x]) => x);
  return xs.every((x, i) => i === 0 || x > xs[i - 1]);
};

test('a straight line needs no refinement', () => {
  const segs = sample(compile('2x + 1'), view);
  assert.equal(segs.length, 1);
  // Exactly the initial grid: width * 0.5 intervals + 1 endpoints.
  assert.equal(pointCount(segs), 201);
  assert.ok(isSorted(segs));
});

test('curved functions get extra samples where needed', () => {
  const line = pointCount(sample(compile('x'), view));
  const wiggly = pointCount(sample(compile('8 sin(4x)'), view));
  assert.ok(wiggly > line, `expected refinement: ${wiggly} vs ${line}`);
});

test('points stay within chord tolerance of the true curve', () => {
  const f = compile('5 sin(2x)');
  const segs = sample(f, view);
  const pxPerUnit = 400 / 20;
  for (const seg of segs) {
    for (let i = 1; i < seg.length; i++) {
      const [x0, y0] = seg[i - 1];
      const [x1, y1] = seg[i];
      const xm = (x0 + x1) / 2;
      const err = Math.abs(f(xm) - (y0 + y1) / 2) * pxPerUnit;
      assert.ok(err <= 1.0, `chord error ${err}px at x=${xm}`);
    }
  }
});

test('tan(x) is broken at its asymptotes instead of joined', () => {
  const segs = sample(compile('tan(x)'), view);
  // Asymptotes at ±π/2, ±3π/2, ±5π/2 within [-10, 10] → 6 breaks → 7 pieces.
  assert.equal(segs.length, 7);
  // No segment may contain a huge vertical jump between neighbours.
  for (const seg of segs) {
    for (let i = 1; i < seg.length; i++) {
      const crossesAsymptote = Math.sign(seg[i][1]) !== Math.sign(seg[i - 1][1])
        && Math.abs(seg[i][1] - seg[i - 1][1]) > 40;
      assert.ok(!crossesAsymptote, `jump inside segment near x=${seg[i][0]}`);
    }
  }
});

test('1/x splits at zero', () => {
  const segs = sample(compile('1/x'), view);
  assert.equal(segs.length, 2);
  assert.ok(segs[0].every(([x]) => x < 0));
  assert.ok(segs[1].every(([x]) => x > 0));
});

test('floor(x) jumps produce separate steps', () => {
  const segs = sample(compile('floor(x)'), view);
  // 20 unit-width steps in [-10, 10]; the right endpoint x=10 is its own step.
  assert.ok(segs.length >= 20, `got ${segs.length} segments`);
  for (const seg of segs) {
    const ys = new Set(seg.map(([, y]) => y));
    assert.equal(ys.size, 1, 'each segment should be one flat step');
  }
});

test('sqrt(x) is only drawn on its domain, close to the boundary', () => {
  const segs = sample(compile('sqrt(x)'), view);
  assert.equal(segs.length, 1);
  const [firstX] = segs[0][0];
  assert.ok(firstX >= 0 && firstX < 0.01, `domain start found at ${firstX}`);
});

test('entirely undefined function yields nothing', () => {
  assert.deepEqual(sample(compile('sqrt(-1 - x^2)'), view), []);
});
