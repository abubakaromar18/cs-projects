import { test } from "node:test";
import assert from "node:assert/strict";
import { Circuit, CircuitError } from "../src/core/circuit.js";
import { GATES, PALETTE, isGateKind, type GateKind } from "../src/core/gates.js";

const B = [false, true] as const;

test("every primitive gate matches its textbook truth table", () => {
  const expected: Record<string, (a: boolean, b: boolean) => boolean> = {
    AND: (a, b) => a && b,
    OR: (a, b) => a || b,
    NAND: (a, b) => !(a && b),
    NOR: (a, b) => !(a || b),
    XOR: (a, b) => a !== b,
    XNOR: (a, b) => a === b,
  };
  for (const [kind, fn] of Object.entries(expected)) {
    for (const a of B) for (const b of B) {
      assert.equal(GATES[kind as GateKind].evaluate([a, b]), fn(a, b), `${kind}(${a},${b})`);
    }
  }
  assert.equal(GATES.NOT.evaluate([true]), false);
  assert.equal(GATES.NOT.evaluate([false]), true);
  assert.equal(GATES.BUFFER.evaluate([true]), true);
});

test("palette only lists known gate kinds", () => {
  for (const k of PALETTE) assert.ok(isGateKind(k));
  assert.equal(isGateKind("FLUX_CAPACITOR"), false);
  assert.equal(isGateKind("toString"), false);
});

test("signals propagate through a chain of gates", () => {
  const c = new Circuit();
  c.addGate("INPUT", 0, 0, { id: "a" });
  c.addGate("NOT", 0, 0, { id: "n1" });
  c.addGate("NOT", 0, 0, { id: "n2" });
  c.addGate("OUTPUT", 0, 0, { id: "out" });
  // Wire in reverse order to prove evaluation order is topological, not insertion order.
  c.connect("n2", "out");
  c.connect("n1", "n2");
  c.connect("a", "n1");
  const r = c.simulate();
  assert.deepEqual(r, { stable: true, sweeps: 1, sequential: false });
  assert.equal(c.value("out"), false);
  c.toggleInput("a");
  c.simulate();
  assert.equal(c.value("n1"), false);
  assert.equal(c.value("out"), true);
});

test("undriven input pins read LOW", () => {
  const c = new Circuit();
  c.addGate("NOT", 0, 0, { id: "n" });
  c.addGate("OR", 0, 0, { id: "o" });
  c.simulate();
  assert.equal(c.value("n"), true);
  assert.equal(c.value("o"), false);
});

test("topological order respects every wire; null when cyclic", () => {
  const c = new Circuit();
  c.addGate("INPUT", 0, 0, { id: "a" });
  c.addGate("INPUT", 0, 0, { id: "b" });
  c.addGate("AND", 0, 0, { id: "g" });
  c.addGate("OUTPUT", 0, 0, { id: "y" });
  c.connect("g", "y");
  c.connect("a", "g", 0);
  c.connect("b", "g", 1);
  const order = c.topologicalOrder()!.map((n) => n.id);
  for (const w of c.allWires()) assert.ok(order.indexOf(w.from) < order.indexOf(w.to), `${w.from} before ${w.to}`);

  c.addGate("NOT", 0, 0, { id: "loop" });
  c.connect("loop", "loop");
  assert.equal(c.topologicalOrder(), null);
});

test("connecting an already-driven pin replaces the old wire", () => {
  const c = new Circuit();
  c.addGate("INPUT", 0, 0, { id: "a", state: true });
  c.addGate("INPUT", 0, 0, { id: "b", state: false });
  c.addGate("OUTPUT", 0, 0, { id: "y" });
  c.connect("a", "y");
  c.connect("b", "y");
  assert.equal(c.allWires().length, 1);
  c.simulate();
  assert.equal(c.value("y"), false);
});

test("fan-out: one output can drive many inputs", () => {
  const c = new Circuit();
  c.addGate("INPUT", 0, 0, { id: "a", state: true });
  for (const id of ["y1", "y2", "y3"]) {
    c.addGate("OUTPUT", 0, 0, { id });
    c.connect("a", id);
  }
  c.simulate();
  assert.deepEqual(c.readOutputs(), { y1: true, y2: true, y3: true });
});

test("invalid connections are rejected", () => {
  const c = new Circuit();
  c.addGate("INPUT", 0, 0, { id: "a" });
  c.addGate("OUTPUT", 0, 0, { id: "y" });
  c.addGate("AND", 0, 0, { id: "g" });
  assert.throws(() => c.connect("y", "g"), CircuitError); // lamp has no output
  assert.throws(() => c.connect("a", "g", 2), CircuitError); // AND has pins 0..1
  assert.throws(() => c.connect("a", "a"), CircuitError); // INPUT has no input pins
  assert.throws(() => c.connect("a", "nope"), CircuitError);
  assert.throws(() => c.addGate("NOT", 0, 0, { id: "a" }), CircuitError);
  assert.throws(() => c.setInput("g", true), CircuitError);
});

test("removing a gate removes its wires", () => {
  const c = new Circuit();
  c.addGate("INPUT", 0, 0, { id: "a" });
  c.addGate("NOT", 0, 0, { id: "n" });
  c.addGate("OUTPUT", 0, 0, { id: "y" });
  c.connect("a", "n");
  c.connect("n", "y");
  c.removeGate("n");
  assert.equal(c.allWires().length, 0);
  assert.equal(c.getNode("n"), undefined);
});

test("a NOT gate feeding itself (ring oscillator) is reported unstable, not an infinite loop", () => {
  const c = new Circuit();
  c.addGate("NOT", 0, 0, { id: "n" });
  c.connect("n", "n");
  const r = c.simulate(50);
  assert.equal(r.stable, false);
  assert.equal(r.sequential, true);
  assert.equal(r.sweeps, 50);
});

test("generated ids never collide with user ids", () => {
  const c = new Circuit();
  c.addGate("AND", 0, 0, { id: "and1" });
  const g = c.addGate("AND");
  assert.notEqual(g.id, "and1");
});
