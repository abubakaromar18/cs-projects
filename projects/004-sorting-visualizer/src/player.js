/**
 * Playback engine: turns a sorting algorithm's event stream into visual state.
 *
 * The Player is pure (no DOM, no timers) so it can be unit tested. The UI
 * calls `step()` on a timer and renders `player.state` after each step.
 */

/**
 * Visual state after replaying some prefix of the event stream.
 * @typedef {object} PlayerState
 * @property {number[]} values     current bar heights
 * @property {Set<number>} sorted  indices known to be in final position
 * @property {number[]} comparing  indices highlighted as being compared
 * @property {number[]} swapping   indices highlighted as being moved
 * @property {number|null} pivot   current pivot index, if any
 * @property {[number, number]|null} range  active subarray, if any
 * @property {{comparisons: number, swaps: number, writes: number, steps: number}} stats
 * @property {boolean} done
 */

export class Player {
  /**
   * @param {(input: number[]) => Generator<object>} algorithm
   * @param {number[]} values
   */
  constructor(algorithm, values) {
    this.algorithm = algorithm;
    this.initial = [...values];
    this.reset();
  }

  /** Rewind to the unsorted input with a fresh generator. */
  reset() {
    this.iterator = this.algorithm(this.initial);
    /** @type {PlayerState} */
    this.state = {
      values: [...this.initial],
      sorted: new Set(),
      comparing: [],
      swapping: [],
      pivot: null,
      range: null,
      stats: { comparisons: 0, swaps: 0, writes: 0, steps: 0 },
      done: false,
    };
  }

  /**
   * Apply the next event. Highlights only last for one step.
   * @returns {object|null} the event applied, or null when finished
   */
  step() {
    if (this.state.done) return null;
    const { value: event, done } = this.iterator.next();
    const s = this.state;
    s.comparing = [];
    s.swapping = [];
    if (done) {
      s.done = true;
      s.pivot = null;
      s.range = null;
      return null;
    }
    s.stats.steps++;
    applyEvent(s, event);
    return event;
  }

  /**
   * Apply up to `n` events (used for fast playback speeds).
   * @returns {number} how many events were applied
   */
  stepMany(n) {
    let applied = 0;
    while (applied < n && this.step()) applied++;
    return applied;
  }

  /** Run to completion and return the final state. */
  finish() {
    while (this.step());
    return this.state;
  }
}

/** Mutate `s` according to a single event. Exported for testing. */
export function applyEvent(s, event) {
  switch (event.type) {
    case 'compare':
      s.stats.comparisons++;
      s.comparing = [event.i, event.j];
      break;
    case 'swap': {
      const { i, j } = event;
      [s.values[i], s.values[j]] = [s.values[j], s.values[i]];
      s.stats.swaps++;
      s.swapping = [i, j];
      // Keep the pivot highlight attached to the pivot value as it moves.
      if (s.pivot === i) s.pivot = j;
      else if (s.pivot === j) s.pivot = i;
      break;
    }
    case 'overwrite':
      s.values[event.i] = event.value;
      s.stats.writes++;
      s.swapping = [event.i];
      break;
    case 'sorted':
      s.sorted.add(event.i);
      if (s.pivot === event.i) s.pivot = null;
      break;
    case 'pivot':
      s.pivot = event.i;
      break;
    case 'range':
      s.range = [event.lo, event.hi];
      break;
    default:
      throw new Error(`Unknown event type: ${event.type}`);
  }
}

/**
 * Map a 1..100 speed slider to a playback schedule.
 * Low speeds slow down one step at a time (up to 500 ms apart); high speeds
 * run every frame and apply several steps per frame (up to 64) so large
 * arrays still finish quickly. The curve is exponential so the slider
 * feels even across the range.
 * @param {number} speed
 * @returns {{delayMs: number, stepsPerTick: number}}
 */
export function playbackRate(speed) {
  const s = Math.min(100, Math.max(1, Number(speed) || 1));
  if (s <= 50) {
    // 1 → 500 ms, 50 → 16 ms (about one frame)
    const t = (s - 1) / 49;
    return { delayMs: Math.round(500 * (16 / 500) ** t), stepsPerTick: 1 };
  }
  // 51 → 1 step per frame ... 100 → 64 steps per frame
  const t = (s - 50) / 50;
  return { delayMs: 16, stepsPerTick: Math.max(1, Math.round(64 ** t)) };
}

/**
 * Small deterministic PRNG (mulberry32) so a seed reproduces an input.
 * @param {number} seed
 * @returns {() => number} function returning floats in [0, 1)
 */
export function mulberry32(seed) {
  let t = seed >>> 0;
  return () => {
    t = (t + 0x6d2b79f5) >>> 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

/** Input shapes that show off best/worst cases of different algorithms. */
export const PRESETS = ['random', 'nearly-sorted', 'reversed', 'few-unique'];

/**
 * Generate an array of `n` bar heights in [1, 100].
 * @param {number} n
 * @param {string} preset one of PRESETS
 * @param {() => number} rand random source (defaults to Math.random)
 * @returns {number[]}
 */
export function generateArray(n, preset = 'random', rand = Math.random) {
  if (!Number.isInteger(n) || n < 0) throw new RangeError('n must be a non-negative integer');
  const randInt = (lo, hi) => lo + Math.floor(rand() * (hi - lo + 1));
  const ascending = () => Array.from({ length: n }, (_, i) => Math.round(1 + (99 * i) / Math.max(1, n - 1)));

  switch (preset) {
    case 'random':
      return Array.from({ length: n }, () => randInt(1, 100));
    case 'reversed':
      return ascending().reverse();
    case 'nearly-sorted': {
      // Sorted, then a handful (~5%) of random adjacent-ish swaps.
      const a = ascending();
      const swaps = Math.max(1, Math.round(n * 0.05));
      for (let k = 0; k < swaps && n > 1; k++) {
        const i = randInt(0, n - 2);
        const j = Math.min(n - 1, i + randInt(1, 3));
        [a[i], a[j]] = [a[j], a[i]];
      }
      return a;
    }
    case 'few-unique': {
      const levels = [20, 45, 70, 95];
      return Array.from({ length: n }, () => levels[randInt(0, levels.length - 1)]);
    }
    default:
      throw new Error(`Unknown preset: ${preset}`);
  }
}
