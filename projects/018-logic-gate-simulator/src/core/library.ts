/**
 * Prebuilt example circuits, constructed programmatically from primitives.
 * These double as executable documentation of how adders and latches work.
 */
import { Circuit } from "./circuit.js";

/** Horizontal/vertical spacing used when laying out generated circuits. */
const COL = 130;

interface AdderPorts {
  sum: string;
  carry: string;
}

/**
 * Half adder: S = A ⊕ B, C = A·B.
 * Adds two bits but cannot accept a carry-in.
 */
export function halfAdder(): Circuit {
  const c = new Circuit();
  c.addGate("INPUT", 40, 80, { id: "A", label: "A" });
  c.addGate("INPUT", 40, 200, { id: "B", label: "B" });
  c.addGate("XOR", 40 + COL * 1.5, 80, { id: "xor" });
  c.addGate("AND", 40 + COL * 1.5, 200, { id: "and" });
  c.addGate("OUTPUT", 40 + COL * 3, 80, { id: "S", label: "S" });
  c.addGate("OUTPUT", 40 + COL * 3, 200, { id: "C", label: "C" });
  c.connect("A", "xor", 0);
  c.connect("B", "xor", 1);
  c.connect("A", "and", 0);
  c.connect("B", "and", 1);
  c.connect("xor", "S");
  c.connect("and", "C");
  c.simulate();
  return c;
}

/**
 * Wire a full adder into an existing circuit from three driver nodes.
 *   S    = (A ⊕ B) ⊕ Cin
 *   Cout = A·B + Cin·(A ⊕ B)
 * Returns the ids of the gates producing sum and carry-out.
 */
export function fullAdderInto(c: Circuit, a: string, b: string, cin: string, x: number, y: number, prefix: string): AdderPorts {
  c.addGate("XOR", x, y, { id: `${prefix}x1` });
  c.addGate("XOR", x + COL, y, { id: `${prefix}x2` });
  c.addGate("AND", x, y + 60, { id: `${prefix}a1` });
  c.addGate("AND", x + COL, y + 60, { id: `${prefix}a2` });
  c.addGate("OR", x + COL * 2, y + 60, { id: `${prefix}o1` });
  c.connect(a, `${prefix}x1`, 0);
  c.connect(b, `${prefix}x1`, 1);
  c.connect(`${prefix}x1`, `${prefix}x2`, 0);
  c.connect(cin, `${prefix}x2`, 1);
  c.connect(a, `${prefix}a1`, 0);
  c.connect(b, `${prefix}a1`, 1);
  c.connect(`${prefix}x1`, `${prefix}a2`, 0);
  c.connect(cin, `${prefix}a2`, 1);
  c.connect(`${prefix}a1`, `${prefix}o1`, 0);
  c.connect(`${prefix}a2`, `${prefix}o1`, 1);
  return { sum: `${prefix}x2`, carry: `${prefix}o1` };
}

/** One-bit full adder with A, B, Cin inputs and S, Cout outputs. */
export function fullAdder(): Circuit {
  const c = new Circuit();
  c.addGate("INPUT", 40, 60, { id: "A", label: "A" });
  c.addGate("INPUT", 40, 140, { id: "B", label: "B" });
  c.addGate("INPUT", 40, 220, { id: "Cin", label: "Cin" });
  const { sum, carry } = fullAdderInto(c, "A", "B", "Cin", 40 + COL * 1.3, 80, "fa");
  c.addGate("OUTPUT", 40 + COL * 4.6, 80, { id: "S", label: "S" });
  c.addGate("OUTPUT", 40 + COL * 4.6, 140, { id: "Cout", label: "Cout" });
  c.connect(sum, "S");
  c.connect(carry, "Cout");
  c.simulate();
  return c;
}

/**
 * n-bit ripple-carry adder: chain n full adders, each carry-out feeding the
 * next stage's carry-in. Inputs A0..A(n-1), B0..B(n-1), Cin; outputs
 * S0..S(n-1), Cout. Bit 0 is least significant. Worst-case delay grows
 * linearly with n because the carry "ripples" through every stage.
 */
export function rippleCarryAdder(bits = 4): Circuit {
  if (!Number.isInteger(bits) || bits < 1 || bits > 16) throw new RangeError("bits must be 1..16");
  const c = new Circuit();
  const ROW = 150;
  c.addGate("INPUT", 40, 20, { id: "Cin", label: "Cin" });
  let carry = "Cin";
  for (let i = 0; i < bits; i++) {
    const y = 90 + i * ROW;
    c.addGate("INPUT", 40, y, { id: `A${i}`, label: `A${i}` });
    c.addGate("INPUT", 40, y + 60, { id: `B${i}`, label: `B${i}` });
    const ports = fullAdderInto(c, `A${i}`, `B${i}`, carry, 40 + COL * 1.3, y, `fa${i}_`);
    c.addGate("OUTPUT", 40 + COL * 4.6, y, { id: `S${i}`, label: `S${i}` });
    c.connect(ports.sum, `S${i}`);
    carry = ports.carry;
  }
  c.addGate("OUTPUT", 40 + COL * 4.6, 90 + bits * ROW - 60, { id: "Cout", label: "Cout" });
  c.connect(carry, "Cout");
  c.simulate();
  return c;
}

/**
 * SR latch from two cross-coupled NOR gates — the simplest memory cell.
 *   S=1,R=0 -> set (Q=1)    S=0,R=1 -> reset (Q=0)
 *   S=0,R=0 -> hold         S=1,R=1 -> invalid (Q = Q̅ = 0)
 * The feedback loop makes this circuit sequential: its output depends on
 * history, not just on the current inputs.
 */
export function srLatch(): Circuit {
  const c = new Circuit();
  c.addGate("INPUT", 40, 80, { id: "R", label: "R" });
  c.addGate("INPUT", 40, 220, { id: "S", label: "S" });
  c.addGate("NOR", 40 + COL * 1.5, 80, { id: "nor1" });
  c.addGate("NOR", 40 + COL * 1.5, 220, { id: "nor2" });
  c.addGate("OUTPUT", 40 + COL * 3, 80, { id: "Q", label: "Q" });
  c.addGate("OUTPUT", 40 + COL * 3, 220, { id: "Qn", label: "Q̅" });
  c.connect("R", "nor1", 0);
  c.connect("nor2", "nor1", 1);
  c.connect("S", "nor2", 1);
  c.connect("nor1", "nor2", 0);
  c.connect("nor1", "Q");
  c.connect("nor2", "Qn");
  c.simulate();
  return c;
}

/**
 * NAND is functionally complete: NOT, AND and OR can all be built from it.
 * Inputs A, B; outputs NOT_A, AND, OR — each using only NAND gates.
 */
export function nandUniversality(): Circuit {
  const c = new Circuit();
  c.addGate("INPUT", 40, 80, { id: "A", label: "A" });
  c.addGate("INPUT", 40, 260, { id: "B", label: "B" });
  // NOT A = A NAND A
  c.addGate("NAND", 200, 20, { id: "notA" });
  c.connect("A", "notA", 0);
  c.connect("A", "notA", 1);
  // A AND B = NOT(A NAND B)
  c.addGate("NAND", 200, 140, { id: "n1" });
  c.addGate("NAND", 340, 140, { id: "and" });
  c.connect("A", "n1", 0);
  c.connect("B", "n1", 1);
  c.connect("n1", "and", 0);
  c.connect("n1", "and", 1);
  // A OR B = (NOT A) NAND (NOT B)
  c.addGate("NAND", 200, 300, { id: "notB" });
  c.addGate("NAND", 340, 260, { id: "or" });
  c.connect("B", "notB", 0);
  c.connect("B", "notB", 1);
  c.connect("notA", "or", 0);
  c.connect("notB", "or", 1);
  c.addGate("OUTPUT", 500, 20, { id: "NOT_A", label: "NOT_A" });
  c.addGate("OUTPUT", 500, 140, { id: "AND", label: "AND" });
  c.addGate("OUTPUT", 500, 260, { id: "OR", label: "OR" });
  c.connect("notA", "NOT_A");
  c.connect("and", "AND");
  c.connect("or", "OR");
  c.simulate();
  return c;
}

export const EXAMPLES: Readonly<Record<string, () => Circuit>> = {
  "Half adder": halfAdder,
  "Full adder": fullAdder,
  "4-bit ripple-carry adder": () => rippleCarryAdder(4),
  "SR latch (NOR)": srLatch,
  "NAND universality": nandUniversality,
};
