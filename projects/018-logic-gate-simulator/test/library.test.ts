import { test } from "node:test";
import assert from "node:assert/strict";
import { EXAMPLES, fullAdder, halfAdder, nandUniversality, rippleCarryAdder, srLatch } from "../src/core/library.js";
import { bitsToNumber, sumOfProducts, truthTable } from "../src/core/analysis.js";
import { fromJSON, toJSON } from "../src/core/serialize.js";
import type { Circuit } from "../src/core/circuit.js";

function set(c: Circuit, values: Record<string, boolean>) {
  for (const [id, v] of Object.entries(values)) c.setInput(id, v);
  return c.simulate();
}

test("half adder truth table", () => {
  const t = truthTable(halfAdder());
  assert.deepEqual(t.inputs, ["A", "B"]);
  assert.deepEqual(t.outputs, ["C", "S"]);
  const asBits = t.rows.map((r) => r.map(Number).join(""));
  // A B | C S
  assert.deepEqual(asBits, ["0000", "0101", "1001", "1110"]);
});

test("full adder: S + 2*Cout === A + B + Cin for all 8 cases", () => {
  const c = fullAdder();
  for (let n = 0; n < 8; n++) {
    const [a, b, cin] = [(n >> 2) & 1, (n >> 1) & 1, n & 1];
    set(c, { A: !!a, B: !!b, Cin: !!cin });
    const { S, Cout } = c.readOutputs();
    assert.equal(Number(S) + 2 * Number(Cout), a + b + cin, `A=${a} B=${b} Cin=${cin}`);
  }
});

test("4-bit ripple-carry adder adds every pair of nibbles (512 cases)", () => {
  const c = rippleCarryAdder(4);
  for (let a = 0; a < 16; a++) {
    for (let b = 0; b < 16; b++) {
      for (const cin of [0, 1]) {
        const inputs: Record<string, boolean> = { Cin: cin === 1 };
        for (let i = 0; i < 4; i++) {
          inputs[`A${i}`] = ((a >> i) & 1) === 1;
          inputs[`B${i}`] = ((b >> i) & 1) === 1;
        }
        const r = set(c, inputs);
        assert.equal(r.sequential, false);
        const sumBits = [0, 1, 2, 3].map((i) => c.value(`S${i}`)).concat(c.value("Cout"));
        assert.equal(bitsToNumber(sumBits), a + b + cin, `${a}+${b}+${cin}`);
      }
    }
  }
});

test("8-bit ripple-carry adder: 200 + 100 = 300", () => {
  const c = rippleCarryAdder(8);
  const inputs: Record<string, boolean> = { Cin: false };
  for (let i = 0; i < 8; i++) {
    inputs[`A${i}`] = ((200 >> i) & 1) === 1;
    inputs[`B${i}`] = ((100 >> i) & 1) === 1;
  }
  set(c, inputs);
  const bits = [...Array(8).keys()].map((i) => c.value(`S${i}`)).concat(c.value("Cout"));
  assert.equal(bitsToNumber(bits), 300);
});

test("SR latch sets, holds, resets and holds again", () => {
  const c = srLatch();
  const q = () => c.readOutputs();

  let r = set(c, { S: true, R: false });
  assert.equal(r.sequential, true);
  assert.equal(r.stable, true);
  assert.deepEqual(q(), { Q: true, "Q̅": false });

  set(c, { S: false, R: false }); // hold: memory!
  assert.deepEqual(q(), { Q: true, "Q̅": false });

  set(c, { S: false, R: true });
  assert.deepEqual(q(), { Q: false, "Q̅": true });

  r = set(c, { S: false, R: false }); // hold the reset state
  assert.equal(r.stable, true);
  assert.deepEqual(q(), { Q: false, "Q̅": true });

  set(c, { S: true, R: true }); // forbidden input: both outputs LOW
  assert.deepEqual(q(), { Q: false, "Q̅": false });
});

test("NAND alone implements NOT, AND and OR", () => {
  const c = nandUniversality();
  for (const a of [false, true]) for (const b of [false, true]) {
    set(c, { A: a, B: b });
    assert.deepEqual(c.readOutputs(), { AND: a && b, NOT_A: !a, OR: a || b });
  }
  const gates = c.allNodes().filter((n) => n.kind !== "INPUT" && n.kind !== "OUTPUT");
  assert.ok(gates.every((g) => g.kind === "NAND"));
});

test("truth table restores the user's switch positions", () => {
  const c = halfAdder();
  set(c, { A: true, B: false });
  truthTable(c);
  assert.equal(c.getNode("A")!.state, true);
  assert.equal(c.getNode("B")!.state, false);
  assert.deepEqual(c.readOutputs(), { C: false, S: true });
});

test("sum-of-products synthesis", () => {
  const t = truthTable(halfAdder());
  assert.equal(sumOfProducts(t, 0), "AB"); // carry
  assert.equal(sumOfProducts(t, 1), "A'B + AB'"); // sum = XOR
});

test("JSON round-trip preserves behaviour for every example", () => {
  for (const [name, build] of Object.entries(EXAMPLES)) {
    const original = build();
    const copy = fromJSON(JSON.parse(JSON.stringify(toJSON(original))));
    assert.deepEqual(truthTable(copy).rows, truthTable(original).rows, name);
  }
});

test("fromJSON rejects malformed input", () => {
  assert.throws(() => fromJSON(null), SyntaxError);
  assert.throws(() => fromJSON({ version: 99, nodes: [], wires: [] }), SyntaxError);
  assert.throws(() => fromJSON({ version: 1, nodes: [{ id: "x", kind: "LASER", x: 0, y: 0 }], wires: [] }), SyntaxError);
  assert.throws(() => fromJSON({ version: 1, nodes: [{ id: "x", kind: "AND", x: "left", y: 0 }], wires: [] }), SyntaxError);
  assert.throws(() => fromJSON({ version: 1, nodes: [], wires: [{ from: "a", to: "b", pin: 0 }] }));
});

test("truth table of a latch does not disturb its memory", () => {
  const c = srLatch();
  set(c, { S: true, R: false });
  set(c, { S: false, R: false }); // holding Q=1
  truthTable(c);
  c.simulate();
  assert.deepEqual(c.readOutputs(), { Q: true, "Q̅": false });
});
