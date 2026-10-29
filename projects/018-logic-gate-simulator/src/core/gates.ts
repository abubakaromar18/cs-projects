/**
 * Gate definitions: every primitive component the simulator knows about.
 *
 * Each gate is described declaratively (arity + a pure boolean function), so
 * the simulation engine never needs a `switch` over gate kinds. Adding a new
 * primitive is a one-line change to GATES below.
 */

/** All component kinds. INPUT is a toggle switch, OUTPUT is a lamp/LED. */
export type GateKind =
  | "INPUT"
  | "OUTPUT"
  | "BUFFER"
  | "NOT"
  | "AND"
  | "OR"
  | "NAND"
  | "NOR"
  | "XOR"
  | "XNOR";

export interface GateSpec {
  /** Number of input pins. */
  readonly inputs: number;
  /** Number of output pins (0 for a lamp, 1 for everything else). */
  readonly outputs: number;
  /** Pure evaluation function. Sources (INPUT) ignore it and use their state. */
  readonly evaluate: (ins: readonly boolean[]) => boolean;
  /** Short symbol drawn inside the gate body. */
  readonly symbol: string;
}

const and = (xs: readonly boolean[]) => xs.every(Boolean);
const or = (xs: readonly boolean[]) => xs.some(Boolean);
/** Odd parity: true when an odd number of inputs are high. */
const xor = (xs: readonly boolean[]) => xs.reduce((acc, x) => acc !== x, false);

export const GATES: Readonly<Record<GateKind, GateSpec>> = {
  INPUT: { inputs: 0, outputs: 1, evaluate: () => false, symbol: "IN" },
  OUTPUT: { inputs: 1, outputs: 0, evaluate: ([a]) => a ?? false, symbol: "OUT" },
  BUFFER: { inputs: 1, outputs: 1, evaluate: ([a]) => a ?? false, symbol: "▷" },
  NOT: { inputs: 1, outputs: 1, evaluate: ([a]) => !a, symbol: "¬" },
  AND: { inputs: 2, outputs: 1, evaluate: and, symbol: "&" },
  OR: { inputs: 2, outputs: 1, evaluate: or, symbol: "≥1" },
  NAND: { inputs: 2, outputs: 1, evaluate: (xs) => !and(xs), symbol: "&̅" },
  NOR: { inputs: 2, outputs: 1, evaluate: (xs) => !or(xs), symbol: "≥1̅" },
  XOR: { inputs: 2, outputs: 1, evaluate: xor, symbol: "=1" },
  XNOR: { inputs: 2, outputs: 1, evaluate: (xs) => !xor(xs), symbol: "=1̅" },
};

/** Gate kinds offered in the editor palette, in display order. */
export const PALETTE: readonly GateKind[] = [
  "INPUT",
  "OUTPUT",
  "BUFFER",
  "NOT",
  "AND",
  "OR",
  "NAND",
  "NOR",
  "XOR",
  "XNOR",
];

export function isGateKind(value: unknown): value is GateKind {
  return typeof value === "string" && Object.prototype.hasOwnProperty.call(GATES, value);
}
