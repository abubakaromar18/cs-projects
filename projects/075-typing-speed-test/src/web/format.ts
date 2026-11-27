/** Pure presentation helpers (no DOM), shared by the UI and tests. */
import type { TimelinePoint } from "../core/session.js";

export function fmtInt(x: number): string {
  return String(Math.round(x));
}

export function fmtPct(x: number): string {
  return `${Math.round(x)}%`;
}

/** 7_500 → "7.5s", 65_000 → "1:05". */
export function fmtDuration(ms: number): string {
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

export interface ChartGeometry {
  /** SVG path for the net-WPM line. */
  wpmPath: string;
  /** SVG path for the burst-WPM line. */
  burstPath: string;
  /** Points where errors happened, for red dots. */
  errorDots: { x: number; y: number; n: number }[];
  maxWpm: number;
}

/**
 * Lay a WPM timeline into a width×height box (origin top-left), with a
 * little headroom so the peak doesn't touch the top edge.
 */
export function chartGeometry(points: readonly TimelinePoint[], width: number, height: number): ChartGeometry {
  if (points.length === 0) return { wpmPath: "", burstPath: "", errorDots: [], maxWpm: 0 };
  const maxWpm = Math.max(10, ...points.map((p) => Math.max(p.wpm, p.burstWpm))) * 1.1;
  const lastSec = points[points.length - 1]!.second || 1;
  const x = (p: TimelinePoint) => round1((p.second / lastSec) * width);
  const y = (v: number) => round1(height - (v / maxWpm) * height);
  const path = (sel: (p: TimelinePoint) => number) =>
    points.map((p, i) => `${i === 0 ? "M" : "L"}${x(p)},${y(sel(p))}`).join(" ");
  return {
    wpmPath: path((p) => p.wpm),
    burstPath: path((p) => p.burstWpm),
    errorDots: points.filter((p) => p.errors > 0).map((p) => ({ x: x(p), y: y(p.burstWpm), n: p.errors })),
    maxWpm,
  };
}

function round1(v: number): number {
  return Math.round(v * 10) / 10;
}

/** Mode id used for personal bests, e.g. "words-25+punct". */
export function modeId(kind: "words" | "time", amount: number, punctuation: boolean, numbers: boolean): string {
  return `${kind}-${amount}${punctuation ? "+punct" : ""}${numbers ? "+num" : ""}`;
}
