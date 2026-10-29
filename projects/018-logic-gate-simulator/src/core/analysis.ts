/**
 * Circuit analysis: exhaustive truth tables and boolean-expression synthesis.
 */
import type { Circuit } from "./circuit.js";

export interface TruthTable {
  readonly inputs: string[];
  readonly outputs: string[];
  /** rows[i] = [...input bits, ...output bits] */
  readonly rows: boolean[][];
}

/** Hard cap: 2^12 = 4096 rows is plenty for an interactive tool. */
export const MAX_TABLE_INPUTS = 12;

/**
 * Enumerate all 2^n input combinations and record the outputs.
 * Input switch positions and internal state (latch memory) are restored
 * afterwards so the editor is unaffected. For sequential circuits the table
 * reflects behaviour starting from the current state.
 * Rows are ordered by counting in binary with the first input as the MSB.
 */
export function truthTable(circuit: Circuit): TruthTable {
  const ins = circuit.inputs();
  const outs = circuit.outputs();
  if (ins.length > MAX_TABLE_INPUTS) {
    throw new RangeError(`Truth table limited to ${MAX_TABLE_INPUTS} inputs (got ${ins.length})`);
  }
  const saved = ins.map((n) => n.state ?? false);
  const state = circuit.snapshotState();
  const rows: boolean[][] = [];
  const total = 1 << ins.length;
  for (let combo = 0; combo < total; combo++) {
    const bits = ins.map((_, i) => ((combo >> (ins.length - 1 - i)) & 1) === 1);
    ins.forEach((n, i) => circuit.setInput(n.id, bits[i]!));
    circuit.simulate();
    rows.push([...bits, ...outs.map((o) => circuit.value(o.id))]);
  }
  ins.forEach((n, i) => circuit.setInput(n.id, saved[i]!));
  circuit.restoreState(state);
  return {
    inputs: ins.map((n) => n.label ?? n.id),
    outputs: outs.map((n) => n.label ?? n.id),
    rows,
  };
}

/**
 * Canonical sum-of-products (disjunctive normal form) for one output column:
 * OR together one minterm per row where the output is 1.
 * e.g. XOR of A,B -> "A'B + AB'".
 */
export function sumOfProducts(table: TruthTable, outputIndex = 0): string {
  const col = table.inputs.length + outputIndex;
  const minterms = table.rows
    .filter((row) => row[col])
    .map((row) => table.inputs.map((name, i) => (row[i] ? name : `${name}'`)).join(""));
  if (minterms.length === 0) return "0";
  if (minterms.length === table.rows.length) return "1";
  return minterms.join(" + ");
}

/** Interpret a list of bits (LSB first) as an unsigned integer. */
export function bitsToNumber(bitsLsbFirst: readonly boolean[]): number {
  return bitsLsbFirst.reduce((acc, bit, i) => acc + (bit ? 2 ** i : 0), 0);
}
