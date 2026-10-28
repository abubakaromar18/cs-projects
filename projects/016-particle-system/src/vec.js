/**
 * Tiny 2D vector helpers and a seeded PRNG.
 *
 * Particles store x/y/vx/vy as plain numbers (not Vec objects) so the hot
 * update loop never allocates; these helpers are used where clarity matters
 * more than raw speed (emitters, force fields, tests).
 */

/** Length of the vector (x, y). */
export const length = (x, y) => Math.hypot(x, y);

/** Clamp v into [lo, hi]. */
export const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

/** Linear interpolation from a to b by t in [0, 1]. */
export const lerp = (a, b, t) => a + (b - a) * t;

/**
 * Mulberry32: a small, fast, seedable PRNG returning floats in [0, 1).
 * Seeding makes simulations reproducible, which is what lets the tests
 * assert on exact behaviour instead of "roughly random".
 */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Uniform float in [lo, hi) using the supplied rng. */
export const range = (rng, lo, hi) => lo + (hi - lo) * rng();

/** Convert an HSL colour (h in degrees, s/l in [0,100]) to a CSS string. */
export const hsl = (h, s, l, a = 1) =>
  `hsla(${((h % 360) + 360) % 360}, ${s}%, ${l}%, ${a})`;
