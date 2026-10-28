/**
 * Firework shell patterns.
 *
 * A pattern is a pure function that returns an array of initial spark
 * velocities (and optional per-spark overrides). Keeping patterns pure — no
 * pool, no canvas — makes them trivial to test and to add new ones.
 */
import { range } from './vec.js';

const TAU = Math.PI * 2;

/** Peony: the classic round burst, sparks spread evenly with a little jitter. */
function peony(rng, count, speed) {
  const out = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * TAU + range(rng, -0.05, 0.05);
    // sqrt keeps the 2D projection of a sphere looking filled, not hollow.
    const s = speed * Math.sqrt(range(rng, 0.15, 1));
    out.push({ vx: Math.cos(a) * s, vy: Math.sin(a) * s });
  }
  return out;
}

/** Ring: every spark at the same speed → a crisp expanding circle. */
function ring(rng, count, speed) {
  const tilt = range(rng, 0.45, 1); // squash vertically for a 3D-ish tilt
  const out = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * TAU;
    out.push({ vx: Math.cos(a) * speed, vy: Math.sin(a) * speed * tilt });
  }
  return out;
}

/**
 * Heart: velocities follow the parametric heart curve
 *   x = 16 sin³t,  y = 13 cos t − 5 cos 2t − 2 cos 3t − cos 4t
 * normalised so the widest point travels at `speed`.
 */
function heart(rng, count, speed) {
  const out = [];
  for (let i = 0; i < count; i++) {
    const t = (i / count) * TAU;
    const x = 16 * Math.sin(t) ** 3;
    const y = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t);
    // Canvas y grows downward, so flip y to keep the heart upright.
    out.push({ vx: (x / 17) * speed, vy: (-y / 17) * speed });
  }
  return out;
}

/** Willow: slow, long-lived, high-drag sparks that droop like branches. */
function willow(rng, count, speed) {
  return peony(rng, count, speed * 0.7).map((v) => ({
    ...v,
    life: range(rng, 2.6, 3.4),
    drag: 2.2,
    trail: 10,
    hueShift: 30, // golden tint relative to the shell hue
  }));
}

/** Spiral: two interleaved arms whose speed grows with angle. */
function spiral(rng, count, speed) {
  const out = [];
  for (let i = 0; i < count; i++) {
    const arm = i % 2;
    const k = i / count;
    const a = k * TAU * 2 + arm * Math.PI;
    const s = speed * (0.25 + 0.75 * k);
    out.push({ vx: Math.cos(a) * s, vy: Math.sin(a) * s });
  }
  return out;
}

export const PATTERNS = Object.freeze({ peony, ring, heart, willow, spiral });
export const PATTERN_NAMES = Object.freeze(Object.keys(PATTERNS));

/**
 * Build a burst description for a pattern name.
 * @returns {Array<{vx:number, vy:number, life?:number, drag?:number, trail?:number, hueShift?:number}>}
 */
export function burst(name, rng, count = 120, speed = 260) {
  const fn = PATTERNS[name];
  if (!fn) throw new Error(`unknown pattern "${name}"`);
  if (count < 0) throw new RangeError('count must be non-negative');
  return fn(rng, count, speed);
}

/**
 * Launch velocity needed for a rocket to peak at height `h` above its start
 * under constant gravity g (ignoring drag): v = √(2·g·h). Returned negative
 * because canvas y points down.
 */
export function launchSpeedFor(h, g) {
  if (h <= 0 || g <= 0) return 0;
  return -Math.sqrt(2 * g * h);
}
