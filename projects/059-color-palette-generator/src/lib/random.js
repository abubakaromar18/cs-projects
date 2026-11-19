/**
 * Seeded pseudo-random number generation.
 *
 * Math.random() can't be replayed, which makes palettes impossible to
 * reproduce or test. mulberry32 is a tiny, fast 32-bit PRNG with good
 * statistical quality for non-cryptographic use: the same seed always
 * yields the same sequence.
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

/** Uniform float in [min, max). */
export const between = (rng, min, max) => min + rng() * (max - min);

/** A fresh random 32-bit seed (non-deterministic). */
export const randomSeed = () => (Math.random() * 2 ** 32) >>> 0;
