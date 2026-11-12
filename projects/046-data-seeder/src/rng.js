/**
 * Seeded pseudo-random number generation.
 *
 * Math.random() cannot be seeded, which makes fake data non-reproducible.
 * Seeding matters for a data seeder: tests, demos, and bug reports all want
 * "the same 50 users as last time". We use two small, well-known algorithms:
 *
 *   - cyrb53-style string hash  -> turns any seed (number or string) into 32 bits
 *   - mulberry32                -> a fast 32-bit PRNG with a full 2^32 period
 */

/** Hash an arbitrary string into an unsigned 32-bit integer. */
export function hashSeed(input) {
  const str = String(input);
  let h1 = 0xdeadbeef ^ str.length;
  let h2 = 0x41c6ce57 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  return h1 >>> 0;
}

/**
 * A deterministic random source with convenience helpers.
 * Every generator receives one of these instead of touching Math.random().
 */
export class Random {
  constructor(seed = Date.now()) {
    this.state = hashSeed(seed);
  }

  /** mulberry32: returns a float in [0, 1). */
  next() {
    let t = (this.state = (this.state + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** Integer in [min, max] inclusive. */
  int(min, max) {
    if (max < min) throw new RangeError(`int(): max (${max}) < min (${min})`);
    return min + Math.floor(this.next() * (max - min + 1));
  }

  /** Float in [min, max) rounded to `decimals` places. */
  float(min, max, decimals = 2) {
    const factor = 10 ** decimals;
    return Math.round((min + this.next() * (max - min)) * factor) / factor;
  }

  /** True with probability p. */
  chance(p) {
    return this.next() < p;
  }

  /** Uniformly pick one element. */
  pick(arr) {
    if (arr.length === 0) throw new RangeError('pick() from empty array');
    return arr[Math.floor(this.next() * arr.length)];
  }

  /**
   * Weighted pick. `weights` is parallel to `items`.
   * Uses a linear scan over the cumulative distribution — fine for small lists.
   */
  weighted(items, weights) {
    const total = weights.reduce((a, b) => a + b, 0);
    let r = this.next() * total;
    for (let i = 0; i < items.length; i++) {
      r -= weights[i];
      if (r < 0) return items[i];
    }
    return items[items.length - 1];
  }

  /** Fisher–Yates shuffle (returns a new array). */
  shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
}
