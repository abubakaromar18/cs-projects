/**
 * Input helpers: map keys and touch/pointer gestures to directions.
 * Kept DOM-free so the gesture math is unit-testable.
 */
import type { Direction } from "./game.js";

const KEYMAP: Record<string, Direction> = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  w: "up",
  s: "down",
  a: "left",
  d: "right",
  k: "up",
  j: "down",
  h: "left",
  l: "right",
};

/** Arrow keys, WASD and vim-style HJKL. Case-insensitive for letters. */
export function keyToDirection(key: string): Direction | null {
  return KEYMAP[key] ?? KEYMAP[key.toLowerCase()] ?? null;
}

export interface Point {
  x: number;
  y: number;
}

export interface SwipeOptions {
  /** Minimum travel in px before a gesture counts as a swipe. */
  minDistance?: number;
  /**
   * How dominant the main axis must be: |major| >= ratio * |minor|.
   * Rejects ambiguous diagonal swipes.
   */
  axisRatio?: number;
  /** Gestures slower than this (ms) are treated as drags, not swipes. */
  maxDuration?: number;
}

/**
 * Classify a gesture from `start` to `end` taking `durationMs`.
 * Screen coordinates: y grows downward, so a positive dy is a swipe down.
 */
export function detectSwipe(
  start: Point,
  end: Point,
  durationMs = 0,
  { minDistance = 24, axisRatio = 1.2, maxDuration = 1000 }: SwipeOptions = {},
): Direction | null {
  if (durationMs > maxDuration) return null;
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const ax = Math.abs(dx);
  const ay = Math.abs(dy);
  if (Math.max(ax, ay) < minDistance) return null;
  if (ax >= ay * axisRatio) return dx > 0 ? "right" : "left";
  if (ay >= ax * axisRatio) return dy > 0 ? "down" : "up";
  return null;
}
