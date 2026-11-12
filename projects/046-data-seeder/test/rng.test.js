import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Random, hashSeed } from '../src/rng.js';

test('same seed produces the same sequence', () => {
  const a = new Random(42);
  const b = new Random(42);
  for (let i = 0; i < 100; i++) assert.equal(a.next(), b.next());
});

test('different seeds diverge', () => {
  const a = new Random('alpha');
  const b = new Random('beta');
  const seqA = Array.from({ length: 10 }, () => a.next());
  const seqB = Array.from({ length: 10 }, () => b.next());
  assert.notDeepEqual(seqA, seqB);
});

test('string and numeric seeds hash to 32-bit unsigned ints', () => {
  for (const s of [0, 1, 'x', 'a much longer seed string']) {
    const h = hashSeed(s);
    assert.ok(Number.isInteger(h) && h >= 0 && h < 2 ** 32);
  }
});

test('next() stays in [0, 1) and int() respects bounds', () => {
  const r = new Random(7);
  for (let i = 0; i < 5000; i++) {
    const x = r.next();
    assert.ok(x >= 0 && x < 1);
    const n = r.int(-3, 3);
    assert.ok(n >= -3 && n <= 3 && Number.isInteger(n));
  }
});

test('int() hits both endpoints', () => {
  const r = new Random(1);
  const seen = new Set(Array.from({ length: 500 }, () => r.int(1, 4)));
  assert.deepEqual([...seen].sort(), [1, 2, 3, 4]);
});

test('int() rejects inverted ranges', () => {
  assert.throws(() => new Random(1).int(5, 1), RangeError);
});

test('weighted() roughly follows weights', () => {
  const r = new Random(99);
  const counts = { a: 0, b: 0 };
  for (let i = 0; i < 10000; i++) counts[r.weighted(['a', 'b'], [9, 1])]++;
  assert.ok(counts.a > 8500 && counts.a < 9500, `got ${counts.a}`);
});

test('shuffle() is a permutation and does not mutate input', () => {
  const input = [1, 2, 3, 4, 5, 6];
  const out = new Random(3).shuffle(input);
  assert.deepEqual(input, [1, 2, 3, 4, 5, 6]);
  assert.deepEqual([...out].sort(), input);
});
