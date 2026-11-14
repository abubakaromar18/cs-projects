/**
 * Synthetic 2-D datasets. All coordinates live in the unit square [0,1]²,
 * so the renderer can scale them to any canvas size.
 *
 * Each generator is deterministic given its seed. A few of them (rings,
 * moons) are deliberately *bad* fits for k-means, which assumes convex,
 * roughly-isotropic clusters — they make the algorithm's limitations visible.
 */
import { mulberry32, gaussian } from './rng.js';

const clamp01 = (x) => Math.min(1, Math.max(0, x));
const pt = (x, y) => ({ x: clamp01(x), y: clamp01(y) });

/**
 * Gaussian blobs around `centers` random centres, or around the explicit
 * `centerPoints` if given.
 */
export function blobs({ n = 300, centers = 4, spread = 0.05, seed = 1, centerPoints = null } = {}) {
  const rand = mulberry32(seed);
  if (centerPoints) centers = centerPoints.length;
  const cs = centerPoints ?? Array.from({ length: centers }, () => ({
    x: 0.15 + rand() * 0.7,
    y: 0.15 + rand() * 0.7,
  }));
  return Array.from({ length: n }, (_, i) => {
    const c = cs[i % centers];
    return pt(c.x + gaussian(rand) * spread, c.y + gaussian(rand) * spread);
  });
}

/** Uniform noise — k-means will still happily "find" k clusters. */
export function uniform({ n = 300, seed = 1 } = {}) {
  const rand = mulberry32(seed);
  return Array.from({ length: n }, () => pt(rand(), rand()));
}

/** Two concentric rings — non-convex, k-means fails. */
export function rings({ n = 300, noise = 0.02, seed = 1 } = {}) {
  const rand = mulberry32(seed);
  return Array.from({ length: n }, (_, i) => {
    const r = i % 2 === 0 ? 0.15 : 0.38;
    const theta = rand() * 2 * Math.PI;
    return pt(
      0.5 + (r + gaussian(rand) * noise) * Math.cos(theta),
      0.5 + (r + gaussian(rand) * noise) * Math.sin(theta),
    );
  });
}

/** Two interleaving half-moons — another classic k-means failure case. */
export function moons({ n = 300, noise = 0.03, seed = 1 } = {}) {
  const rand = mulberry32(seed);
  return Array.from({ length: n }, (_, i) => {
    const t = rand() * Math.PI;
    const upper = i % 2 === 0;
    const x = upper ? Math.cos(t) : 1 - Math.cos(t);
    const y = upper ? Math.sin(t) : 0.5 - Math.sin(t);
    // Map the ~[-1,2]×[-0.5,1] moon space into the unit square.
    return pt(0.15 + (x + 1) * 0.233 + gaussian(rand) * noise,
              0.75 - (y + 0.5) * 0.35 + gaussian(rand) * noise);
  });
}

/** Clusters with very different sizes/densities — shows k-means' equal-variance bias. */
export function anisotropic({ n = 300, seed = 1 } = {}) {
  const rand = mulberry32(seed);
  const groups = [
    { x: 0.25, y: 0.3, sx: 0.12, sy: 0.02, w: 0.45 },
    { x: 0.7, y: 0.7, sx: 0.03, sy: 0.03, w: 0.2 },
    { x: 0.7, y: 0.25, sx: 0.08, sy: 0.08, w: 0.35 },
  ];
  return Array.from({ length: n }, () => {
    let r = rand();
    let g = groups[groups.length - 1];
    for (const cand of groups) { if ((r -= cand.w) < 0) { g = cand; break; } }
    return pt(g.x + gaussian(rand) * g.sx, g.y + gaussian(rand) * g.sy);
  });
}

export const DATASETS = { blobs, uniform, rings, moons, anisotropic };
