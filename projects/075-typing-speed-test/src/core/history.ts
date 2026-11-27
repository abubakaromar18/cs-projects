/**
 * Persistent run history and lifetime per-key stats.
 *
 * Storage is injected (anything with getItem/setItem) so the logic runs in
 * Node tests with an in-memory map and in the browser with localStorage.
 * Every access is wrapped: private windows and blocked storage throw, and a
 * corrupted value must never break the app.
 */
import { mergeKeyStats } from "./heatmap.js";
import type { KeyStats } from "./session.js";

export interface KVStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface RunRecord {
  at: string; // ISO timestamp
  mode: string; // e.g. "words-25" or "time-30"
  netWpm: number;
  rawWpm: number;
  accuracy: number;
  consistency: number;
  durationMs: number;
}

interface Persisted {
  version: 1;
  runs: RunRecord[];
  keyStats: KeyStats;
}

const KEY = "typing-speed-test:v1";
const MAX_RUNS = 200;

export class History {
  private data: Persisted;

  constructor(private readonly store: KVStore | null) {
    this.data = this.load();
  }

  get runs(): readonly RunRecord[] {
    return this.data.runs;
  }

  get lifetimeKeyStats(): KeyStats {
    return this.data.keyStats;
  }

  /** Record a run; returns true if it's a new personal best for its mode. */
  add(run: RunRecord, keyStats: KeyStats): boolean {
    const prevBest = this.best(run.mode);
    this.data.runs.push(run);
    if (this.data.runs.length > MAX_RUNS) this.data.runs.splice(0, this.data.runs.length - MAX_RUNS);
    this.data.keyStats = mergeKeyStats(this.data.keyStats, keyStats);
    this.save();
    return prevBest === null || run.netWpm > prevBest.netWpm;
  }

  best(mode: string): RunRecord | null {
    let best: RunRecord | null = null;
    for (const r of this.data.runs) if (r.mode === mode && (!best || r.netWpm > best.netWpm)) best = r;
    return best;
  }

  /** Mean net WPM of the last n runs (any mode), or null. */
  recentAverage(n = 10): number | null {
    const xs = this.data.runs.slice(-n);
    return xs.length ? xs.reduce((a, r) => a + r.netWpm, 0) / xs.length : null;
  }

  clear(): void {
    this.data = empty();
    this.save();
  }

  private load(): Persisted {
    try {
      const raw = this.store?.getItem(KEY);
      if (!raw) return empty();
      const parsed = JSON.parse(raw) as Partial<Persisted>;
      if (parsed.version !== 1 || !Array.isArray(parsed.runs) || typeof parsed.keyStats !== "object") {
        return empty();
      }
      return { version: 1, runs: parsed.runs, keyStats: parsed.keyStats ?? {} };
    } catch {
      return empty();
    }
  }

  private save(): void {
    try {
      this.store?.setItem(KEY, JSON.stringify(this.data));
    } catch {
      /* storage full or unavailable: history just won't persist */
    }
  }
}

function empty(): Persisted {
  return { version: 1, runs: [], keyStats: {} };
}
