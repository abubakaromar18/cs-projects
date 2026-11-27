/**
 * TypingSession: the core state machine of a test.
 *
 * It owns the target text and the user's typed buffer, logs every keystroke
 * with a timestamp, and derives all statistics from that log. Time is always
 * passed in by the caller (milliseconds), which keeps the class pure and
 * trivially testable — the browser passes performance.now().
 *
 * Definitions (the conventional ones used by most typing tests):
 *   - A "word" is 5 characters, including spaces.
 *   - Raw WPM  = (all characters typed into the buffer / 5) / minutes.
 *   - Net WPM  = (correct characters in the buffer / 5) / minutes.
 *     Errors you fix with backspace stop costing you speed but still cost
 *     accuracy; errors left in place lower net WPM.
 *   - Accuracy = correct keystrokes / total character keystrokes.
 */
import { keyIdFor } from "./keyboard.js";

export type KeystrokeKind = "char" | "backspace";

export interface Keystroke {
  kind: KeystrokeKind;
  /** ms timestamp supplied by the caller. */
  at: number;
  /** Index in the target the keystroke applied to. */
  index: number;
  /** Character typed (char only). */
  typed?: string;
  /** Character that was expected at that index (char only). */
  expected?: string;
  correct?: boolean;
}

export interface KeyStat {
  /** Times this key was the expected key. */
  attempts: number;
  /** Times the expected key was typed wrongly. */
  misses: number;
  /** Sum of latencies (ms since previous keystroke) for correct hits. */
  latencyTotal: number;
  /** Number of latencies counted in latencyTotal. */
  latencyCount: number;
}

export type KeyStats = Record<string, KeyStat>;

export interface SessionStats {
  elapsedMs: number;
  rawWpm: number;
  netWpm: number;
  /** 0–100 */
  accuracy: number;
  correctChars: number;
  incorrectChars: number;
  /** Errors made then corrected. */
  correctedErrors: number;
  totalKeystrokes: number;
  /** 0–100; how even the rhythm was (100 = perfectly regular intervals). */
  consistency: number;
  progress: number;
}

export interface TimelinePoint {
  /** End of the bucket, seconds since start. */
  second: number;
  /** Net WPM over the whole test up to this point. */
  wpm: number;
  /** Raw WPM inside just this bucket. */
  burstWpm: number;
  errors: number;
}

export type SessionState = "ready" | "running" | "finished";

export class TypingSession {
  readonly target: string;
  private buffer: string[] = [];
  private readonly log: Keystroke[] = [];
  private startedAt: number | null = null;
  private finishedAt: number | null = null;

  constructor(target: string) {
    if (target.length === 0) throw new Error("target text must not be empty");
    this.target = target;
  }

  get state(): SessionState {
    if (this.finishedAt !== null) return "finished";
    return this.startedAt === null ? "ready" : "running";
  }

  /** Method form of state === "finished" (avoids stale TS narrowing after mutations). */
  isFinished(): boolean {
    return this.finishedAt !== null;
  }

  get typed(): string {
    return this.buffer.join("");
  }

  get keystrokes(): readonly Keystroke[] {
    return this.log;
  }

  /** Cursor position = number of characters currently in the buffer. */
  get cursor(): number {
    return this.buffer.length;
  }

  /**
   * Type a single character. Returns whether it matched the target.
   * The clock starts on the first keystroke; the test finishes the moment
   * the buffer reaches the target length.
   */
  type(ch: string, at: number): boolean {
    if ([...ch].length !== 1) throw new Error("type() takes exactly one character");
    if (this.state === "finished") return false;
    if (this.startedAt === null) this.startedAt = at;

    const index = this.buffer.length;
    const expected = this.target[index]!;
    const correct = ch === expected;
    this.buffer.push(ch);
    this.log.push({ kind: "char", at, index, typed: ch, expected, correct });

    if (this.buffer.length >= this.target.length) this.finishedAt = at;
    return correct;
  }

  /** Delete the previous character, if any. */
  backspace(at: number): void {
    if (this.state !== "running" || this.buffer.length === 0) return;
    this.buffer.pop();
    this.log.push({ kind: "backspace", at, index: this.buffer.length });
  }

  /** Delete back to the start of the current word (Ctrl+Backspace). */
  backspaceWord(at: number): void {
    while (this.buffer.length > 0 && this.buffer[this.buffer.length - 1] === " ") this.backspace(at);
    while (this.buffer.length > 0 && this.buffer[this.buffer.length - 1] !== " ") this.backspace(at);
  }

  /** Force-stop (e.g. a timed test ran out). */
  finish(at: number): void {
    if (this.state === "finished") return;
    if (this.startedAt === null) this.startedAt = at;
    this.finishedAt = at;
  }

  /** Per-position status for rendering the passage. */
  charStatus(index: number): "pending" | "correct" | "incorrect" {
    if (index >= this.buffer.length) return "pending";
    return this.buffer[index] === this.target[index] ? "correct" : "incorrect";
  }

  elapsed(now: number): number {
    if (this.startedAt === null) return 0;
    return Math.max(0, (this.finishedAt ?? now) - this.startedAt);
  }

  stats(now: number): SessionStats {
    const elapsedMs = this.elapsed(now);
    let correctChars = 0;
    for (let i = 0; i < this.buffer.length; i++) {
      if (this.buffer[i] === this.target[i]) correctChars++;
    }
    const incorrectChars = this.buffer.length - correctChars;

    const charStrokes = this.log.filter((k) => k.kind === "char");
    const correctStrokes = charStrokes.filter((k) => k.correct).length;
    const wrongStrokes = charStrokes.length - correctStrokes;

    return {
      elapsedMs,
      rawWpm: wpm(this.buffer.length, elapsedMs),
      netWpm: wpm(correctChars, elapsedMs),
      accuracy: charStrokes.length === 0 ? 100 : (100 * correctStrokes) / charStrokes.length,
      correctChars,
      incorrectChars,
      correctedErrors: Math.max(0, wrongStrokes - incorrectChars),
      totalKeystrokes: this.log.length,
      consistency: consistency(intervals(this.log)),
      progress: this.buffer.length / this.target.length,
    };
  }

  /**
   * Per physical key statistics, keyed by keyboard key id (so "A" and "a"
   * share a key). Each char keystroke is attributed to the key that was
   * *expected*: a miss on "e" means you failed to hit "e". Latency is the
   * gap since the previous keystroke, counted only for correct hits and
   * capped so that pauses (reading ahead, distractions) don't skew it.
   */
  keyStats(maxLatencyMs = 2000): KeyStats {
    const stats: KeyStats = {};
    let prevAt: number | null = null;
    for (const ks of this.log) {
      if (ks.kind === "char") {
        const id = keyIdFor(ks.expected!) ?? ks.expected!;
        const s = (stats[id] ??= { attempts: 0, misses: 0, latencyTotal: 0, latencyCount: 0 });
        s.attempts++;
        if (!ks.correct) s.misses++;
        else if (prevAt !== null) {
          const dt = ks.at - prevAt;
          if (dt <= maxLatencyMs) {
            s.latencyTotal += dt;
            s.latencyCount++;
          }
        }
      }
      prevAt = ks.at;
    }
    return stats;
  }

  /**
   * WPM over time, bucketed. Replays the keystroke log so the buffer state
   * at each bucket boundary is exact (including backspaces).
   */
  timeline(bucketMs = 1000): TimelinePoint[] {
    if (this.startedAt === null) return [];
    const start = this.startedAt;
    const end = this.finishedAt ?? this.log[this.log.length - 1]?.at ?? start;
    const buckets = Math.max(1, Math.ceil((end - start) / bucketMs));
    const points: TimelinePoint[] = [];
    const buf: string[] = [];
    let li = 0;
    for (let b = 1; b <= buckets; b++) {
      const boundary = b === buckets ? end : start + b * bucketMs;
      let typedInBucket = 0;
      let errors = 0;
      while (li < this.log.length && this.log[li]!.at <= boundary) {
        const ks = this.log[li++]!;
        if (ks.kind === "char") {
          buf.push(ks.typed!);
          typedInBucket++;
          if (!ks.correct) errors++;
        } else buf.pop();
      }
      let correct = 0;
      for (let i = 0; i < buf.length; i++) if (buf[i] === this.target[i]) correct++;
      const bucketStart = start + (b - 1) * bucketMs;
      points.push({
        second: Math.round((boundary - start) / 100) / 10,
        wpm: wpm(correct, boundary - start),
        burstWpm: wpm(typedInBucket, boundary - bucketStart),
        errors,
      });
    }
    return points;
  }
}

/** Characters-per-5 over minutes; 0 when no time has elapsed. */
export function wpm(chars: number, ms: number): number {
  if (ms <= 0) return 0;
  return chars / 5 / (ms / 60000);
}

function intervals(log: readonly Keystroke[]): number[] {
  const out: number[] = [];
  for (let i = 1; i < log.length; i++) out.push(log[i]!.at - log[i - 1]!.at);
  return out;
}

/**
 * Rhythm consistency from the coefficient of variation (stddev / mean) of
 * inter-key intervals, mapped to 0–100. CV 0 → 100%, CV ≥ 1 → 0%.
 */
export function consistency(xs: readonly number[]): number {
  if (xs.length < 2) return 100;
  const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
  if (mean <= 0) return 100;
  const variance = xs.reduce((a, x) => a + (x - mean) ** 2, 0) / xs.length;
  const cv = Math.sqrt(variance) / mean;
  return Math.max(0, Math.min(100, 100 * (1 - cv)));
}
