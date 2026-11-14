/**
 * Cluster-quality metrics used to help choose k.
 */
import { kmeansBestOf } from './kmeans.js';

/**
 * Mean silhouette coefficient in [-1, 1]. For each point i:
 *   a(i) = mean distance to other points in its own cluster
 *   b(i) = smallest mean distance to the points of any other cluster
 *   s(i) = (b - a) / max(a, b)
 * Points in singleton clusters score 0 (Rousseeuw's convention).
 * O(n²) — fine for the few hundred points in the visualizer.
 */
export function silhouette(points, assignments, k) {
  const n = points.length;
  if (k < 2 || n < 2) return 0;
  const sizes = new Array(k).fill(0);
  for (const a of assignments) sizes[a]++;
  let total = 0;
  const sums = new Array(k);
  for (let i = 0; i < n; i++) {
    sums.fill(0);
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      sums[assignments[j]] += Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y);
    }
    const own = assignments[i];
    if (sizes[own] <= 1) continue; // s(i) = 0
    const a = sums[own] / (sizes[own] - 1);
    let b = Infinity;
    for (let c = 0; c < k; c++) {
      if (c !== own && sizes[c] > 0) b = Math.min(b, sums[c] / sizes[c]);
    }
    if (!Number.isFinite(b)) continue;
    const m = Math.max(a, b);
    total += m === 0 ? 0 : (b - a) / m;
  }
  return total / n;
}

/**
 * Elbow curve: best-of-restarts inertia for each k in [kMin, kMax].
 * @returns {{k:number, inertia:number, silhouette:number}[]}
 */
export function elbowCurve(points, { kMin = 1, kMax = 8, restarts = 5, seed = 1 } = {}) {
  const out = [];
  for (let k = kMin; k <= Math.min(kMax, points.length); k++) {
    const res = kmeansBestOf(points, { k, restarts, seed });
    out.push({ k, inertia: res.inertia, silhouette: silhouette(points, res.assignments, k) });
  }
  return out;
}

/**
 * Pick the "elbow" as the k whose point lies farthest above the straight line
 * joining the first and last points of the normalised curve (a "kneedle"-style
 * heuristic). Inertia typically falls by orders of magnitude, so by default we
 * work on log(inertia); otherwise the huge k=1→2 drop dominates and the elbow
 * is almost always reported too early.
 */
export function findElbow(curve, { log = true } = {}) {
  if (curve.length < 3) return curve.length ? curve[0].k : null;
  const f = (v) => (log ? Math.log(Math.max(v, 1e-12)) : v);
  const pts = curve.map((p) => ({ k: p.k, inertia: f(p.inertia) }));
  const first = pts[0];
  const last = pts[pts.length - 1];
  const spanK = last.k - first.k;
  const spanI = first.inertia - last.inertia || 1;
  let best = first.k;
  let bestD = -Infinity;
  for (const p of pts) {
    // Normalise both axes to [0,1] so the scale of inertia doesn't dominate.
    const x = (p.k - first.k) / spanK;
    const y = (first.inertia - p.inertia) / spanI;
    const d = y - x; // distance above the diagonal y = x (up to a constant factor)
    if (d > bestD) { bestD = d; best = p.k; }
  }
  return best;
}
