/**
 * K-means clustering (Lloyd's algorithm) exposed as a *generator of steps*.
 *
 * Instead of returning only the final answer, `kmeansSteps` yields an event
 * after each phase so the UI can animate the algorithm one move at a time:
 *
 *   { type: 'init',   centroids, assignments }   – initial centroids chosen
 *   { type: 'assign', centroids, assignments, changed } – E-step: points → nearest centroid
 *   { type: 'update', centroids, assignments, shift }   – M-step: centroids → cluster mean
 *   { type: 'done',   centroids, assignments, iterations, inertia, reason }
 *
 * Every event carries fresh copies of the arrays, so consumers may keep
 * a history (for "step back") without aliasing bugs.
 *
 * Complexity: each iteration is O(n·k·d); with d = 2 here.
 */
import { mulberry32, randInt } from './rng.js';

/** Squared Euclidean distance (we never need the sqrt for comparisons). */
export function dist2(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return dx * dx + dy * dy;
}

/** Index of the nearest centroid to point p. Ties go to the lowest index. */
export function nearest(p, centroids) {
  let best = 0;
  let bestD = Infinity;
  for (let j = 0; j < centroids.length; j++) {
    const d = dist2(p, centroids[j]);
    if (d < bestD) { bestD = d; best = j; }
  }
  return best;
}

/** Within-cluster sum of squared distances (the objective k-means minimises). */
export function inertia(points, centroids, assignments) {
  let s = 0;
  for (let i = 0; i < points.length; i++) s += dist2(points[i], centroids[assignments[i]]);
  return s;
}

// ---------------------------------------------------------------------------
// Initialisation strategies
// ---------------------------------------------------------------------------

/** Forgy: pick k distinct data points uniformly at random. */
export function initForgy(points, k, rand) {
  const idx = points.map((_, i) => i);
  // Partial Fisher–Yates shuffle: only the first k slots matter.
  for (let i = 0; i < k; i++) {
    const j = i + randInt(rand, idx.length - i);
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return idx.slice(0, k).map((i) => ({ ...points[i] }));
}

/** Random partition: assign every point a random cluster, centroids = means. */
export function initRandomPartition(points, k, rand) {
  const assignments = points.map(() => randInt(rand, k));
  return computeCentroids(points, assignments, k, initForgy(points, k, rand));
}

/**
 * k-means++ (Arthur & Vassilvitskii, 2007): the first centroid is uniform;
 * each subsequent one is drawn with probability ∝ D(x)², the squared distance
 * to the closest centroid chosen so far. This spreads seeds out and gives an
 * O(log k)-competitive expected result.
 */
export function initKMeansPlusPlus(points, k, rand) {
  const centroids = [{ ...points[randInt(rand, points.length)] }];
  const d2 = points.map((p) => dist2(p, centroids[0]));
  while (centroids.length < k) {
    const total = d2.reduce((a, b) => a + b, 0);
    let chosen;
    if (total === 0) {
      chosen = randInt(rand, points.length); // all points coincide with centroids
    } else {
      let r = rand() * total;
      chosen = points.length - 1;
      for (let i = 0; i < points.length; i++) {
        r -= d2[i];
        if (r < 0) { chosen = i; break; }
      }
    }
    const c = { ...points[chosen] };
    centroids.push(c);
    for (let i = 0; i < points.length; i++) d2[i] = Math.min(d2[i], dist2(points[i], c));
  }
  return centroids;
}

export const INIT_METHODS = {
  'kmeans++': initKMeansPlusPlus,
  forgy: initForgy,
  'random-partition': initRandomPartition,
};

/**
 * M-step: each centroid moves to the mean of its assigned points.
 * An empty cluster keeps its previous position (`fallback[j]`) so k stays fixed.
 */
export function computeCentroids(points, assignments, k, fallback) {
  const sx = new Array(k).fill(0);
  const sy = new Array(k).fill(0);
  const cnt = new Array(k).fill(0);
  for (let i = 0; i < points.length; i++) {
    const j = assignments[i];
    sx[j] += points[i].x;
    sy[j] += points[i].y;
    cnt[j]++;
  }
  return sx.map((_, j) =>
    cnt[j] > 0 ? { x: sx[j] / cnt[j], y: sy[j] / cnt[j] } : { ...fallback[j] });
}

/**
 * Step generator for Lloyd's algorithm.
 * @param {{x:number,y:number}[]} points
 * @param {object} opts
 * @param {number} opts.k
 * @param {'kmeans++'|'forgy'|'random-partition'} [opts.init]
 * @param {{x:number,y:number}[]} [opts.centroids] - explicit initial centroids (overrides init)
 * @param {number} [opts.seed]
 * @param {number} [opts.maxIter]
 * @param {number} [opts.tol] - stop when total centroid movement falls below tol
 */
export function* kmeansSteps(points, { k, init = 'kmeans++', centroids: given, seed = 1, maxIter = 100, tol = 1e-9 } = {}) {
  if (!Number.isInteger(k) || k < 1) throw new RangeError('k must be a positive integer');
  if (points.length < k) throw new RangeError(`need at least k=${k} points, got ${points.length}`);
  const rand = mulberry32(seed);

  let centroids;
  if (given) {
    if (given.length !== k) throw new RangeError('initial centroids length must equal k');
    centroids = given.map((c) => ({ ...c }));
  } else {
    const fn = INIT_METHODS[init];
    if (!fn) throw new RangeError(`unknown init method "${init}"`);
    centroids = fn(points, k, rand);
  }
  let assignments = new Array(points.length).fill(-1);
  yield { type: 'init', centroids: clonePts(centroids), assignments: [...assignments] };

  for (let iter = 1; iter <= maxIter; iter++) {
    // E-step: reassign every point to its nearest centroid.
    let changed = 0;
    const next = points.map((p, i) => {
      const j = nearest(p, centroids);
      if (j !== assignments[i]) changed++;
      return j;
    });
    assignments = next;
    yield { type: 'assign', iteration: iter, centroids: clonePts(centroids), assignments: [...assignments], changed };

    if (changed === 0) {
      return yield done(points, centroids, assignments, iter, 'assignments stable');
    }

    // M-step: move centroids to the mean of their members.
    const moved = computeCentroids(points, assignments, k, centroids);
    let shift = 0;
    for (let j = 0; j < k; j++) shift += Math.sqrt(dist2(moved[j], centroids[j]));
    centroids = moved;
    yield { type: 'update', iteration: iter, centroids: clonePts(centroids), assignments: [...assignments], shift };

    if (shift <= tol) {
      return yield done(points, centroids, assignments, iter, 'centroids converged');
    }
  }
  return yield done(points, centroids, assignments, maxIter, 'max iterations reached');
}

function done(points, centroids, assignments, iterations, reason) {
  return {
    type: 'done',
    centroids: clonePts(centroids),
    assignments: [...assignments],
    iterations,
    inertia: inertia(points, centroids, assignments),
    reason,
  };
}

const clonePts = (ps) => ps.map((p) => ({ x: p.x, y: p.y }));

/** Run to completion and return the final 'done' event. */
export function kmeans(points, opts) {
  let last;
  for (const ev of kmeansSteps(points, opts)) last = ev;
  return last;
}

/** Best of `restarts` runs (lowest inertia) — standard defence against bad local minima. */
export function kmeansBestOf(points, { restarts = 10, seed = 1, ...opts }) {
  let best = null;
  for (let r = 0; r < restarts; r++) {
    const res = kmeans(points, { ...opts, seed: seed + r * 7919 });
    if (!best || res.inertia < best.inertia) best = res;
  }
  return best;
}
