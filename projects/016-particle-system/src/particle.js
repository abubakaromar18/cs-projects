/**
 * Particle state and a fixed-capacity object pool.
 *
 * A fireworks show spawns and kills thousands of short-lived particles per
 * second. Allocating a fresh object for each would churn the garbage
 * collector and cause visible frame hitches, so particles are recycled from
 * a pool: `acquire()` hands out a dead slot, `release()` returns it.
 */

/** Particle kinds: a rocket climbs and explodes; a spark just fades. */
export const KIND = Object.freeze({ SPARK: 0, ROCKET: 1 });

export class Particle {
  constructor() {
    this.reset();
  }

  /** Return every field to a neutral, dead state. */
  reset() {
    this.alive = false;
    this.kind = KIND.SPARK;
    this.x = 0; this.y = 0;      // position (px)
    this.vx = 0; this.vy = 0;    // velocity (px/s)
    this.ax = 0; this.ay = 0;    // accumulated acceleration this step (px/s²)
    this.mass = 1;
    this.age = 0;                // seconds since spawn
    this.life = 1;               // lifetime in seconds
    this.hue = 0;
    this.size = 2;
    this.drag = 1;               // multiplier on global drag (sparks > rockets)
    this.trail = 0;              // number of trail points to remember
    this.history = [];           // previous positions for trail rendering
    this.payload = null;         // rocket only: what to spawn on explosion
    return this;
  }

  /** Fraction of life remaining in [0, 1]; drives fade-out. */
  get vitality() {
    return this.life <= 0 ? 0 : Math.max(0, 1 - this.age / this.life);
  }

  /** Add a force (F = m·a ⇒ a = F / m) for the current step. */
  applyForce(fx, fy) {
    this.ax += fx / this.mass;
    this.ay += fy / this.mass;
  }
}

export class ParticlePool {
  /** @param {number} capacity hard cap on simultaneously live particles */
  constructor(capacity) {
    if (!Number.isInteger(capacity) || capacity <= 0) {
      throw new RangeError('capacity must be a positive integer');
    }
    this.capacity = capacity;
    this.items = Array.from({ length: capacity }, () => new Particle());
    // Free list as a stack of indices: O(1) acquire and release.
    this.free = [];
    for (let i = capacity - 1; i >= 0; i--) this.free.push(i);
    this.indexOf = new Map(this.items.map((p, i) => [p, i]));
  }

  get liveCount() {
    return this.capacity - this.free.length;
  }

  /**
   * Take a dead particle from the pool, reset and mark it alive.
   * Returns null when the pool is exhausted; callers simply drop the spawn,
   * which degrades gracefully instead of growing memory without bound.
   */
  acquire() {
    if (this.free.length === 0) return null;
    const p = this.items[this.free.pop()].reset();
    p.alive = true;
    return p;
  }

  /** Return a particle to the pool. Releasing twice is a no-op. */
  release(p) {
    if (!p.alive) return;
    const i = this.indexOf.get(p);
    if (i === undefined) throw new Error('particle does not belong to this pool');
    p.alive = false;
    p.history.length = 0;
    this.free.push(i);
  }
}
