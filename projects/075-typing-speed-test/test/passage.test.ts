import { test } from "node:test";
import assert from "node:assert/strict";
import { generatePassage, buildFocusPool } from "../src/core/passage.js";
import { mulberry32 } from "../src/core/random.js";
import { COMMON_WORDS } from "../src/core/words.js";

test("mulberry32 is deterministic and in [0,1)", () => {
  const a = mulberry32(42), b = mulberry32(42);
  for (let i = 0; i < 1000; i++) {
    const x = a();
    assert.equal(x, b());
    assert.ok(x >= 0 && x < 1);
  }
});

test("passage has exactly N words from the vocabulary, no immediate repeats", () => {
  const p = generatePassage({ words: 300 }, mulberry32(1));
  const ws = p.split(" ");
  assert.equal(ws.length, 300);
  const vocab = new Set(COMMON_WORDS);
  for (let i = 0; i < ws.length; i++) {
    assert.ok(vocab.has(ws[i]!), ws[i]);
    if (i > 0) assert.notEqual(ws[i], ws[i - 1]);
  }
});

test("same seed → same passage", () => {
  assert.equal(generatePassage({ words: 20 }, mulberry32(7)), generatePassage({ words: 20 }, mulberry32(7)));
});

test("punctuation capitalises sentence starts and ends with a period", () => {
  const p = generatePassage({ words: 200, punctuation: true }, mulberry32(3));
  assert.match(p, /^[A-Z]/);
  assert.ok(p.endsWith("."));
  for (const m of p.matchAll(/[.?!] (\S)/g)) assert.match(m[1]!, /[A-Z]/);
  assert.match(p, /,/);
});

test("numbers option inserts digits", () => {
  const p = generatePassage({ words: 300, numbers: true }, mulberry32(5));
  assert.match(p, /\b\d+\b/);
});

test("focus keys bias the passage toward words containing them", () => {
  const count = (p: string) => [...p].filter((c) => c === "z" || c === "q").length;
  const plain = generatePassage({ words: 500 }, mulberry32(9));
  const focused = generatePassage({ words: 500, focusKeys: ["z", "q"], focusWeight: 0.8 }, mulberry32(9));
  assert.ok(count(focused) > 5 * Math.max(1, count(plain)), `${count(focused)} vs ${count(plain)}`);
});

test("buildFocusPool weights by number of focus keys", () => {
  const pool = buildFocusPool(["zebra", "jazz", "cat"], ["z"]);
  assert.deepEqual(pool.sort(), ["jazz", "jazz", "zebra"]);
  assert.deepEqual(buildFocusPool(["cat"], []), []);
});

test("invalid word count throws", () => {
  assert.throws(() => generatePassage({ words: 0 }, mulberry32(1)), RangeError);
});
