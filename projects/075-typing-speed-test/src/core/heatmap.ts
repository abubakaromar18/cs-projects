/**
 * Turns per-key statistics into a renderable heatmap model: every key on
 * the layout gets a 0–1 intensity and a colour on a green→yellow→red ramp.
 *
 * Two modes:
 *   - "errors":  intensity = smoothed miss rate (Laplace/Bayesian prior so a
 *                single miss on a key seen once isn't shown as 100% red).
 *   - "latency": intensity = average correct-hit latency, normalised between
 *                the fastest and slowest keys of this run.
 */
import { allKeys, QWERTY_ROWS, type KeyDef } from "./keyboard.js";
import type { KeyStat, KeyStats } from "./session.js";

export type HeatmapMode = "errors" | "latency";

export interface HeatCell {
  key: KeyDef;
  attempts: number;
  misses: number;
  /** Raw miss rate (0–1) or null when the key was never expected. */
  errorRate: number | null;
  /** Mean ms for correct hits, or null. */
  avgLatency: number | null;
  /** 0 (good) … 1 (bad), or null if no data. */
  intensity: number | null;
  /** CSS colour, or null if no data. */
  color: string | null;
}

export interface HeatmapOptions {
  mode: HeatmapMode;
  /** Pseudo-count prior for error smoothing (default 2 attempts, 0 misses). */
  priorAttempts?: number;
  /** Error rate considered "fully red" (default 0.25). */
  maxErrorRate?: number;
}

export function buildHeatmap(stats: KeyStats, opts: HeatmapOptions): HeatCell[][] {
  const prior = opts.priorAttempts ?? 2;
  const maxErr = opts.maxErrorRate ?? 0.25;

  const latencies = Object.values(stats)
    .map(avgLatency)
    .filter((x): x is number => x !== null);
  const lo = Math.min(...latencies);
  const hi = Math.max(...latencies);

  return QWERTY_ROWS.map((row) =>
    row.map((key): HeatCell => {
      const s = stats[key.id];
      const attempts = s?.attempts ?? 0;
      const misses = s?.misses ?? 0;
      const lat = s ? avgLatency(s) : null;
      let intensity: number | null = null;
      if (attempts > 0) {
        if (opts.mode === "errors") {
          const smoothed = misses / (attempts + prior);
          intensity = clamp01(smoothed / maxErr);
        } else if (lat !== null) {
          intensity = hi > lo ? (lat - lo) / (hi - lo) : 0;
        }
      }
      return {
        key,
        attempts,
        misses,
        errorRate: attempts > 0 ? misses / attempts : null,
        avgLatency: lat,
        intensity,
        color: intensity === null ? null : heatColor(intensity),
      };
    }),
  );
}

export function avgLatency(s: KeyStat): number | null {
  return s.latencyCount > 0 ? s.latencyTotal / s.latencyCount : null;
}

/**
 * Keys ranked worst-first by smoothed error rate, ties broken by latency.
 * Only letter keys with enough samples are considered — these feed the
 * adaptive "practice weak keys" passage generator.
 */
export function weakestKeys(stats: KeyStats, n = 5, minAttempts = 3): string[] {
  return allKeys()
    .filter((k) => /^[a-z]$/.test(k.id))
    .map((k) => ({ id: k.id, s: stats[k.id] }))
    .filter((x): x is { id: string; s: KeyStat } => !!x.s && x.s.attempts >= minAttempts)
    .map(({ id, s }) => ({ id, err: s.misses / (s.attempts + 2), lat: avgLatency(s) ?? 0 }))
    .sort((a, b) => b.err - a.err || b.lat - a.lat)
    .slice(0, n)
    .map((x) => x.id);
}

/** Merge two KeyStats (used to accumulate lifetime stats across runs). */
export function mergeKeyStats(a: KeyStats, b: KeyStats): KeyStats {
  const out: KeyStats = {};
  for (const src of [a, b]) {
    for (const [id, s] of Object.entries(src)) {
      const t = (out[id] ??= { attempts: 0, misses: 0, latencyTotal: 0, latencyCount: 0 });
      t.attempts += s.attempts;
      t.misses += s.misses;
      t.latencyTotal += s.latencyTotal;
      t.latencyCount += s.latencyCount;
    }
  }
  return out;
}

/** Linear interpolation green (120°) → yellow (60°) → red (0°) in HSL. */
export function heatColor(t: number): string {
  const hue = Math.round(120 * (1 - clamp01(t)));
  return `hsl(${hue} 75% 50%)`;
}

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}
