/**
 * Deterministic pseudo-random number generation.
 *
 * Math.random() cannot be seeded, which makes clustering runs impossible to
 * reproduce (and impossible to unit-test). We use mulberry32, a tiny 32-bit
 * generator with good statistical quality for visual/educational purposes.
 */

/**
 * Create a seeded PRNG returning floats in [0, 1).
 * @param {number} seed - any integer; the same seed yields the same sequence.
 * @returns {() => number}
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

/**
 * Standard-normal sample via the Box–Muller transform.
 * @param {() => number} rand - uniform [0,1) source
 */
export function gaussian(rand) {
  // 1 - rand() keeps u in (0, 1] so log(u) is finite.
  const u = 1 - rand();
  const v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Integer in [0, n). */
export function randInt(rand, n) {
  return Math.floor(rand() * n);
}
