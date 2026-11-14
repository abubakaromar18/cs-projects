import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DATASETS } from '../src/datasets.js';
import { mulberry32, gaussian } from '../src/rng.js';
import { StepPlayer } from '../src/player.js';
import { kmeansSteps } from '../src/kmeans.js';
import { voronoiCells, colorFor, PALETTE } from '../src/renderer.js';

test('rng is deterministic and in range; gaussian has ~zero mean', () => {
  const a = mulberry32(5); const b = mulberry32(5);
  for (let i = 0; i < 100; i++) {
    const x = a();
    assert.equal(x, b());
    assert.ok(x >= 0 && x < 1);
  }
  const r = mulberry32(1);
  let s = 0;
  for (let i = 0; i < 20000; i++) s += gaussian(r);
  assert.ok(Math.abs(s / 20000) < 0.03);
});

test('every dataset yields n points inside the unit square, deterministically', () => {
  for (const [name, gen] of Object.entries(DATASETS)) {
    const pts = gen({ n: 123, seed: 4 });
    assert.equal(pts.length, 123, name);
    assert.ok(pts.every((p) => p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1), name);
    assert.deepEqual(pts, gen({ n: 123, seed: 4 }), name);
  }
});

test('StepPlayer steps forward, back, to end, and resets', () => {
  const pts = DATASETS.blobs({ n: 80, seed: 1 });
  const p = new StepPlayer(() => kmeansSteps(pts, { k: 3, seed: 2 }));
  assert.equal(p.current.type, 'init');
  assert.ok(p.atStart);
  p.forward();
  assert.equal(p.current.type, 'assign');
  p.back();
  assert.equal(p.current.type, 'init');
  p.back();
  assert.equal(p.current.type, 'init', 'back at start is a no-op');
  const end = p.toEnd();
  assert.equal(end.type, 'done');
  assert.ok(p.atEnd);
  const len = p.history.length;
  p.forward();
  assert.equal(p.history.length, len, 'forward at end is a no-op');
  p.back(); p.forward();
  assert.equal(p.current.type, 'done', 'replays history after stepping back');
  p.reset();
  assert.equal(p.history.length, 1);
});

test('voronoiCells labels grid cells by nearest centroid', () => {
  const cells = voronoiCells([{ x: 0.25, y: 0.5 }, { x: 0.75, y: 0.5 }], 4, 2);
  assert.deepEqual([...cells], [0, 0, 1, 1, 0, 0, 1, 1]);
  assert.equal(colorFor(0), PALETTE[0]);
  assert.equal(colorFor(PALETTE.length), PALETTE[0]);
});
