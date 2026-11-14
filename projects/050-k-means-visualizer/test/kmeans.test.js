import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  kmeans, kmeansSteps, kmeansBestOf, nearest, dist2, inertia, computeCentroids,
  initKMeansPlusPlus, initForgy, initRandomPartition,
} from '../src/kmeans.js';
import { blobs } from '../src/datasets.js';
import { mulberry32 } from '../src/rng.js';

const square = [
  { x: 0, y: 0 }, { x: 0.1, y: 0 }, { x: 0, y: 0.1 },
  { x: 1, y: 1 }, { x: 0.9, y: 1 }, { x: 1, y: 0.9 },
];

test('dist2 and nearest', () => {
  assert.equal(dist2({ x: 0, y: 0 }, { x: 3, y: 4 }), 25);
  assert.equal(nearest({ x: 0.2, y: 0.2 }, [{ x: 1, y: 1 }, { x: 0, y: 0 }]), 1);
  assert.equal(nearest({ x: 0.5, y: 0.5 }, [{ x: 0, y: 0 }, { x: 1, y: 1 }]), 0, 'ties go to lowest index');
});

test('computeCentroids takes means and keeps empty clusters in place', () => {
  const c = computeCentroids(square, [0, 0, 0, 1, 1, 1], 3, [{}, {}, { x: 0.5, y: 0.5 }]);
  assert.ok(Math.abs(c[0].x - 0.1 / 3) < 1e-12);
  assert.ok(Math.abs(c[1].y - 2.9 / 3) < 1e-12);
  assert.deepEqual(c[2], { x: 0.5, y: 0.5 });
});

test('separates two obvious clusters', () => {
  const res = kmeans(square, { k: 2, seed: 3 });
  assert.equal(res.type, 'done');
  const [a, b] = [res.assignments[0], res.assignments[3]];
  assert.notEqual(a, b);
  assert.deepEqual(res.assignments, [a, a, a, b, b, b]);
});

test('steps follow init → (assign, update)* → assign/update → done', () => {
  const events = [...kmeansSteps(square, { k: 2, seed: 1 })];
  assert.equal(events[0].type, 'init');
  assert.ok(events[0].assignments.every((x) => x === -1));
  assert.equal(events.at(-1).type, 'done');
  for (let i = 1; i < events.length - 1; i++) {
    const want = i % 2 === 1 ? 'assign' : 'update';
    assert.equal(events[i].type, want, `event ${i}`);
  }
});

test('events are independent snapshots (no aliasing)', () => {
  const events = [...kmeansSteps(blobs({ n: 60, seed: 2 }), { k: 3, init: 'forgy', seed: 5 })];
  events[0].centroids[0].x = 999;
  assert.notEqual(events[1].centroids[0].x, 999);
});

test('inertia never increases between successive assign/update phases', () => {
  const pts = blobs({ n: 400, centers: 5, spread: 0.08, seed: 9 });
  for (const init of ['kmeans++', 'forgy', 'random-partition']) {
    let prev = Infinity;
    for (const ev of kmeansSteps(pts, { k: 5, init, seed: 4 })) {
      if (ev.type === 'init') continue;
      const j = inertia(pts, ev.centroids, ev.assignments);
      assert.ok(j <= prev + 1e-12, `${init}: inertia rose ${prev} → ${j}`);
      prev = j;
    }
  }
});

test('deterministic for a fixed seed', () => {
  const pts = blobs({ n: 200, seed: 4 });
  assert.deepEqual(kmeans(pts, { k: 4, seed: 42 }), kmeans(pts, { k: 4, seed: 42 }));
});

test('explicit initial centroids are honoured', () => {
  const [ev] = kmeansSteps(square, { k: 2, centroids: [{ x: 0.3, y: 0.3 }, { x: 0.7, y: 0.7 }] });
  assert.deepEqual(ev.centroids, [{ x: 0.3, y: 0.3 }, { x: 0.7, y: 0.7 }]);
});

test('k = 1 centroid is the global mean; k = n gives zero inertia', () => {
  const one = kmeans(square, { k: 1 });
  assert.ok(Math.abs(one.centroids[0].x - 0.5) < 1e-12);
  const all = kmeans(square, { k: square.length, init: 'forgy', seed: 2 });
  assert.ok(all.inertia < 1e-12);
});

test('maxIter stops the run', () => {
  const pts = blobs({ n: 300, centers: 6, spread: 0.12, seed: 1 });
  const res = kmeans(pts, { k: 6, init: 'forgy', maxIter: 1, seed: 3 });
  assert.equal(res.iterations, 1);
});

test('validates arguments', () => {
  assert.throws(() => kmeans(square, { k: 0 }), RangeError);
  assert.throws(() => kmeans(square, { k: 7 }), RangeError);
  assert.throws(() => kmeans(square, { k: 2, init: 'nope' }), RangeError);
  assert.throws(() => kmeans(square, { k: 2, centroids: [{ x: 0, y: 0 }] }), RangeError);
});

test('init methods return k distinct-ish centroids', () => {
  const pts = blobs({ n: 100, seed: 3 });
  for (const fn of [initKMeansPlusPlus, initForgy, initRandomPartition]) {
    const cs = fn(pts, 4, mulberry32(1));
    assert.equal(cs.length, 4);
  }
  const forgy = initForgy(pts, 10, mulberry32(1));
  assert.equal(new Set(forgy.map((c) => `${c.x},${c.y}`)).size, 10);
});

test('k-means++ handles duplicate points without crashing', () => {
  const dup = Array.from({ length: 10 }, () => ({ x: 0.5, y: 0.5 }));
  const cs = initKMeansPlusPlus(dup, 3, mulberry32(1));
  assert.equal(cs.length, 3);
  assert.equal(kmeans(dup, { k: 3 }).inertia, 0);
});

test('k-means++ beats Forgy on average for well-separated blobs', () => {
  const pts = blobs({ n: 400, centers: 8, spread: 0.02, seed: 21 });
  const avg = (init) => {
    let s = 0;
    for (let seed = 1; seed <= 20; seed++) s += kmeans(pts, { k: 8, init, seed }).inertia;
    return s / 20;
  };
  assert.ok(avg('kmeans++') <= avg('forgy'));
});

test('best-of restarts is no worse than any single run', () => {
  const pts = blobs({ n: 300, centers: 6, spread: 0.06, seed: 5 });
  const best = kmeansBestOf(pts, { k: 6, init: 'forgy', restarts: 8, seed: 1 });
  const single = kmeans(pts, { k: 6, init: 'forgy', seed: 1 });
  assert.ok(best.inertia <= single.inertia);
});
