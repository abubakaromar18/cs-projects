import { test } from 'node:test';
import assert from 'node:assert/strict';
import { silhouette, elbowCurve, findElbow } from '../src/metrics.js';
import { kmeans } from '../src/kmeans.js';
import { blobs, uniform } from '../src/datasets.js';

test('silhouette is high for well-separated clusters and ~0 when k < 2', () => {
  const pts = blobs({ n: 200, centers: 3, spread: 0.02, seed: 8 });
  const res = kmeans(pts, { k: 3, seed: 1 });
  assert.ok(silhouette(pts, res.assignments, 3) > 0.7);
  assert.equal(silhouette(pts, res.assignments.map(() => 0), 1), 0);
});

test('silhouette is lower for uniform noise than for blobs', () => {
  const b = blobs({ n: 200, centers: 4, spread: 0.03, seed: 2 });
  const u = uniform({ n: 200, seed: 2 });
  const sb = silhouette(b, kmeans(b, { k: 4 }).assignments, 4);
  const su = silhouette(u, kmeans(u, { k: 4 }).assignments, 4);
  assert.ok(sb > su);
});

test('silhouette stays within [-1, 1] for an arbitrary labelling', () => {
  const pts = uniform({ n: 50, seed: 3 });
  const s = silhouette(pts, pts.map((_, i) => i % 3), 3);
  assert.ok(s >= -1 && s <= 1);
});

test('elbow curve inertia is non-increasing in k', () => {
  const pts = blobs({ n: 240, centers: 4, spread: 0.03, seed: 6 });
  const curve = elbowCurve(pts, { kMax: 8, restarts: 5 });
  assert.equal(curve.length, 8);
  for (let i = 1; i < curve.length; i++) assert.ok(curve[i].inertia <= curve[i - 1].inertia + 1e-9);
});

test('findElbow recovers the true number of well-separated blobs', () => {
  const layouts = {
    3: [{ x: 0.2, y: 0.2 }, { x: 0.8, y: 0.25 }, { x: 0.5, y: 0.8 }],
    4: [{ x: 0.2, y: 0.2 }, { x: 0.8, y: 0.2 }, { x: 0.2, y: 0.8 }, { x: 0.8, y: 0.8 }],
    5: [{ x: 0.15, y: 0.15 }, { x: 0.85, y: 0.15 }, { x: 0.5, y: 0.5 }, { x: 0.15, y: 0.85 }, { x: 0.85, y: 0.85 }],
  };
  for (const [k, centerPoints] of Object.entries(layouts)) {
    const pts = blobs({ n: 300, spread: 0.03, seed: 6, centerPoints });
    const curve = elbowCurve(pts, { kMax: 9, restarts: 6 });
    assert.equal(findElbow(curve), Number(k), `layout with ${k} blobs`);
  }
});

test('findElbow on a synthetic curve and edge cases', () => {
  const curve = [100, 40, 10, 8, 7, 6].map((inertia, i) => ({ k: i + 1, inertia }));
  assert.equal(findElbow(curve, { log: false }), 3);
  assert.equal(findElbow(curve), 3);
  assert.equal(findElbow([]), null);
  assert.equal(findElbow([{ k: 1, inertia: 5 }]), 1);
});
