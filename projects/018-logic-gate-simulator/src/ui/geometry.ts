/**
 * Pure layout math for drawing gates and wires. No DOM access, so it is
 * unit-testable in Node.
 */
import { GATES, type GateKind } from "../core/gates.js";

export interface Point {
  x: number;
  y: number;
}

export interface Size {
  w: number;
  h: number;
}

export const PIN_RADIUS = 6;

export function gateSize(kind: GateKind): Size {
  if (kind === "INPUT" || kind === "OUTPUT") return { w: 56, h: 40 };
  return { w: 72, h: 52 };
}

/** Position of input pin `pin` on a gate whose top-left corner is (x, y). */
export function inputPinPos(kind: GateKind, x: number, y: number, pin: number): Point {
  const { h } = gateSize(kind);
  const n = GATES[kind].inputs;
  return { x, y: y + (h * (pin + 1)) / (n + 1) };
}

/** Position of the single output pin. */
export function outputPinPos(kind: GateKind, x: number, y: number): Point {
  const { w, h } = gateSize(kind);
  return { x: x + w, y: y + h / 2 };
}

/**
 * SVG path for a wire: a horizontal-tangent cubic Bézier, which reads like a
 * hand-drawn schematic and never overlaps the gate bodies at its ends.
 */
export function wirePath(a: Point, b: Point): string {
  const dx = Math.max(40, Math.abs(b.x - a.x) / 2);
  return `M ${a.x} ${a.y} C ${a.x + dx} ${a.y}, ${b.x - dx} ${b.y}, ${b.x} ${b.y}`;
}

/** Snap a coordinate to the background grid. */
export function snap(v: number, grid = 10): number {
  return Math.round(v / grid) * grid;
}
