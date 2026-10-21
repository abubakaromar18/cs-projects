/**
 * Pomodoro timer core — a small, framework-free state machine.
 *
 * The timer never relies on setInterval ticks for accuracy. Instead it stores
 * the wall-clock instant the current phase will end (`endsAt`) and derives the
 * remaining time from an injected clock. This keeps the countdown correct even
 * when the browser throttles background tabs, and makes the logic trivially
 * testable with a fake clock.
 *
 * States:   idle ──start──▶ running ──pause──▶ paused ──resume──▶ running
 *                              │                                      │
 *                              └────────── phase ends / skip ─────────┘
 *                                          ▼
 *                                next phase (idle, or running if autoStart)
 */

export const Phase = Object.freeze({
  WORK: 'work',
  SHORT_BREAK: 'shortBreak',
  LONG_BREAK: 'longBreak',
});

export const Status = Object.freeze({
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
});

export const DEFAULT_SETTINGS = Object.freeze({
  workMinutes: 25,
  shortBreakMinutes: 5,
  longBreakMinutes: 15,
  longBreakInterval: 4, // a long break after every N work sessions
  autoStartNext: false,
});

const MINUTE = 60_000;

/** Validate and normalise user settings, falling back to defaults. */
export function normalizeSettings(input = {}) {
  const s = { ...DEFAULT_SETTINGS, ...input };
  const clampInt = (v, lo, hi, fallback) => {
    const n = Math.round(Number(v));
    return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback;
  };
  return {
    workMinutes: clampInt(s.workMinutes, 1, 180, DEFAULT_SETTINGS.workMinutes),
    shortBreakMinutes: clampInt(s.shortBreakMinutes, 1, 60, DEFAULT_SETTINGS.shortBreakMinutes),
    longBreakMinutes: clampInt(s.longBreakMinutes, 1, 120, DEFAULT_SETTINGS.longBreakMinutes),
    longBreakInterval: clampInt(s.longBreakInterval, 1, 12, DEFAULT_SETTINGS.longBreakInterval),
    autoStartNext: Boolean(s.autoStartNext),
  };
}

/** Length of a phase in milliseconds for the given settings. */
export function phaseDuration(phase, settings) {
  switch (phase) {
    case Phase.WORK: return settings.workMinutes * MINUTE;
    case Phase.SHORT_BREAK: return settings.shortBreakMinutes * MINUTE;
    case Phase.LONG_BREAK: return settings.longBreakMinutes * MINUTE;
    default: throw new Error(`Unknown phase: ${phase}`);
  }
}

/**
 * Decide which phase follows `phase`.
 * @param {string} phase           the phase that just finished
 * @param {number} completedWork   work sessions completed in this cycle (after finishing)
 */
export function nextPhase(phase, completedWork, settings) {
  if (phase !== Phase.WORK) return Phase.WORK;
  return completedWork > 0 && completedWork % settings.longBreakInterval === 0
    ? Phase.LONG_BREAK
    : Phase.SHORT_BREAK;
}

/** Format milliseconds as MM:SS (rounding up so 0:00 only shows at the end). */
export function formatTime(ms) {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export class PomodoroTimer {
  /**
   * @param {object} opts
   * @param {object} [opts.settings]   partial settings, merged with defaults
   * @param {() => number} [opts.now]  clock in ms (injected for testing)
   */
  constructor({ settings = {}, now = () => Date.now() } = {}) {
    this.now = now;
    this.settings = normalizeSettings(settings);
    this.listeners = new Map();
    this.phase = Phase.WORK;
    this.status = Status.IDLE;
    this.completedWork = 0; // work sessions finished in the current cycle
    this.remaining = phaseDuration(this.phase, this.settings);
    this.endsAt = null;
  }

  // ── tiny event emitter ────────────────────────────────────────────────
  on(event, fn) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(fn);
    return () => this.listeners.get(event).delete(fn);
  }

  emit(event, payload) {
    for (const fn of this.listeners.get(event) ?? []) fn(payload);
  }

  // ── queries ──────────────────────────────────────────────────────────
  /** Remaining milliseconds in the current phase. */
  getRemaining() {
    if (this.status === Status.RUNNING) return Math.max(0, this.endsAt - this.now());
    return this.remaining;
  }

  /** Fraction of the current phase that has elapsed, 0..1. */
  getProgress() {
    const total = phaseDuration(this.phase, this.settings);
    return 1 - this.getRemaining() / total;
  }

  snapshot() {
    return {
      phase: this.phase,
      status: this.status,
      remaining: this.getRemaining(),
      progress: this.getProgress(),
      completedWork: this.completedWork,
    };
  }

  // ── commands ─────────────────────────────────────────────────────────
  start() {
    if (this.status === Status.RUNNING) return;
    this.endsAt = this.now() + this.remaining;
    this.status = Status.RUNNING;
    this.emit('change', this.snapshot());
  }

  pause() {
    if (this.status !== Status.RUNNING) return;
    this.remaining = this.getRemaining();
    this.endsAt = null;
    this.status = Status.PAUSED;
    this.emit('change', this.snapshot());
  }

  toggle() {
    if (this.status === Status.RUNNING) this.pause();
    else this.start();
  }

  /** Reset the current phase back to its full length, stopped. */
  reset() {
    this.status = Status.IDLE;
    this.endsAt = null;
    this.remaining = phaseDuration(this.phase, this.settings);
    this.emit('change', this.snapshot());
  }

  /** Abandon the current phase and move on without counting it as completed. */
  skip() {
    this.advance({ completed: false });
  }

  /** Apply new settings; an idle timer picks up the new phase length. */
  updateSettings(partial) {
    this.settings = normalizeSettings({ ...this.settings, ...partial });
    if (this.status === Status.IDLE) this.remaining = phaseDuration(this.phase, this.settings);
    this.emit('change', this.snapshot());
  }

  /**
   * Call periodically (e.g. from requestAnimationFrame or setInterval).
   * Detects phase completion and emits 'tick' / 'complete' events.
   */
  tick() {
    if (this.status !== Status.RUNNING) return;
    if (this.getRemaining() <= 0) {
      this.advance({ completed: true });
    } else {
      this.emit('tick', this.snapshot());
    }
  }

  /** Internal: transition to the next phase. */
  advance({ completed }) {
    const finished = this.phase;
    const duration = phaseDuration(finished, this.settings);
    if (finished === Phase.WORK && completed) this.completedWork += 1;

    const upcoming = nextPhase(finished, this.completedWork, this.settings);
    // A long break closes a cycle; start counting the next one from zero.
    if (finished === Phase.LONG_BREAK) this.completedWork = 0;

    if (completed) {
      this.emit('complete', { phase: finished, duration, next: upcoming, at: this.now() });
    }

    this.phase = upcoming;
    this.remaining = phaseDuration(upcoming, this.settings);
    this.endsAt = null;
    this.status = Status.IDLE;
    if (completed && this.settings.autoStartNext) this.start();
    else this.emit('change', this.snapshot());
  }
}
