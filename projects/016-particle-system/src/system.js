/**
 * The particle system: owns the pool, the force list and the clock.
 *
 * Simulation uses a fixed timestep with an accumulator ("Fix Your
 * Timestep"). Rendering runs at whatever rate the browser gives us, but
 * physics always advances in equal `dt` slices, so behaviour is identical on
 * a 60 Hz laptop and a 144 Hz monitor — and deterministic for tests.
 *
 * Integration is semi-implicit (symplectic) Euler: update velocity from
 * acceleration first, then position from the *new* velocity. It costs the
 * same as explicit Euler but is far more stable for oscillating and
 * orbiting motion (e.g. particles circling an attractor).
 */
import { KIND, ParticlePool } from './particle.js';
import { burst, launchSpeedFor, PATTERN_NAMES } from './fireworks.js';
import { gravity, drag, wind } from './forces.js';
import { mulberry32, range } from './vec.js';

export class ParticleSystem {
  /**
   * @param {object} opts
   * @param {number} [opts.width]     world width in px
   * @param {number} [opts.height]    world height in px
   * @param {number} [opts.capacity]  max live particles
   * @param {number} [opts.dt]        fixed step in seconds
   * @param {number} [opts.seed]      PRNG seed for reproducible shows
   */
  constructor({ width = 800, height = 600, capacity = 6000, dt = 1 / 120, seed = 1 } = {}) {
    this.width = width;
    this.height = height;
    this.dt = dt;
    this.pool = new ParticlePool(capacity);
    this.rng = mulberry32(seed);
    this.time = 0;
    this.accumulator = 0;
    this.maxStepsPerFrame = 10; // guards against the "spiral of death"
    this.forces = [gravity(), drag(), wind(0)];
    this.stats = { spawned: 0, dropped: 0, explosions: 0 };
    this.onExplode = null; // optional hook (e.g. for sound/flash effects)
  }

  /** All currently live particles (allocates; for rendering and tests). */
  live() {
    return this.pool.items.filter((p) => p.alive);
  }

  addForce(force) { this.forces.push(force); return force; }

  removeForce(force) {
    const i = this.forces.indexOf(force);
    if (i >= 0) this.forces.splice(i, 1);
  }

  findForce(name) { return this.forces.find((f) => f.name === name); }

  /** Acquire a particle and initialise it from `props`; counts drops. */
  spawn(props) {
    const p = this.pool.acquire();
    if (!p) { this.stats.dropped++; return null; }
    Object.assign(p, props);
    this.stats.spawned++;
    return p;
  }

  /**
   * Fire a rocket from (x, groundY) that peaks near `targetY` and then
   * bursts into `pattern`. The fuse is the time to apex (v/g), so the shell
   * explodes at the top of its arc, just like a real one.
   */
  launch(x, targetY, { pattern, hue, count = 120, speed = 260 } = {}) {
    const g = this.findForce('gravity')?.g ?? 300;
    const startY = this.height;
    const vy = launchSpeedFor(startY - targetY, g);
    const fuse = vy === 0 ? 0 : -vy / g;
    return this.spawn({
      kind: KIND.ROCKET,
      x, y: startY,
      vx: range(this.rng, -15, 15),
      vy,
      life: fuse,
      size: 2.5,
      drag: 0, // rockets cut through the air; drag would make them fall short
      trail: 6,
      hue: hue ?? Math.floor(range(this.rng, 0, 360)),
      payload: {
        pattern: pattern ?? PATTERN_NAMES[Math.floor(this.rng() * PATTERN_NAMES.length)],
        count,
        speed,
      },
    });
  }

  /** Spawn a burst of sparks at (x, y) — what a rocket does when its fuse ends. */
  explode(x, y, { pattern = 'peony', hue = 0, count = 120, speed = 260, vx = 0, vy = 0 } = {}) {
    this.stats.explosions++;
    const sparks = burst(pattern, this.rng, count, speed);
    for (const s of sparks) {
      this.spawn({
        kind: KIND.SPARK,
        x, y,
        // Sparks inherit the shell's momentum.
        vx: vx + s.vx,
        vy: vy + s.vy,
        life: s.life ?? range(this.rng, 1.1, 1.9),
        size: range(this.rng, 1.2, 2.4),
        drag: s.drag ?? 1,
        trail: s.trail ?? 3,
        hue: hue + (s.hueShift ?? 0) + range(this.rng, -12, 12),
        mass: range(this.rng, 0.8, 1.2),
      });
    }
    this.onExplode?.({ x, y, pattern, hue });
  }

  /** Advance exactly one fixed step. */
  step() {
    const dt = this.dt;
    const t = this.time;
    for (const p of this.pool.items) {
      if (!p.alive) continue;

      // 1. Accumulate forces.
      p.ax = 0; p.ay = 0;
      for (const f of this.forces) if (f.enabled) f.apply(p, t);

      // 2. Semi-implicit Euler.
      p.vx += p.ax * dt;
      p.vy += p.ay * dt;
      if (p.trail > 0) {
        p.history.push(p.x, p.y);
        if (p.history.length > p.trail * 2) p.history.splice(0, 2);
      }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.age += dt;

      // 3. Lifecycle: rockets explode, sparks die; anything off-world is culled.
      if (p.age >= p.life) {
        if (p.kind === KIND.ROCKET && p.payload) {
          const { x, y, vx, vy, hue, payload } = p;
          this.pool.release(p); // free the slot first so the burst can use it
          this.explode(x, y, { ...payload, hue, vx: vx * 0.3, vy: vy * 0.3 });
        } else {
          this.pool.release(p);
        }
      } else if (p.y > this.height + 50 || p.x < -200 || p.x > this.width + 200) {
        this.pool.release(p);
      }
    }
    this.time += dt;
  }

  /**
   * Feed real elapsed time; runs as many fixed steps as fit.
   * @returns {{ steps: number, alpha: number }} alpha is the leftover
   *   fraction of a step, usable for render interpolation.
   */
  advance(elapsed) {
    this.accumulator += Math.max(0, elapsed);
    let steps = 0;
    while (this.accumulator >= this.dt && steps < this.maxStepsPerFrame) {
      this.step();
      this.accumulator -= this.dt;
      steps++;
    }
    // If we fell too far behind (tab was hidden), drop the backlog rather
    // than trying to simulate minutes of time in one frame.
    if (steps === this.maxStepsPerFrame) this.accumulator = 0;
    return { steps, alpha: this.accumulator / this.dt };
  }

  /** Total kinetic energy ½·m·v² of live particles — a handy diagnostic. */
  kineticEnergy() {
    let e = 0;
    for (const p of this.pool.items) {
      if (p.alive) e += 0.5 * p.mass * (p.vx * p.vx + p.vy * p.vy);
    }
    return e;
  }

  resize(width, height) { this.width = width; this.height = height; }

  clear() {
    for (const p of this.pool.items) this.pool.release(p);
  }
}
