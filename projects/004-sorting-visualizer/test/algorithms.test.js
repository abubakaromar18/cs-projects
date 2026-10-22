import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ALGORITHMS, bubbleSort, quickSort, mergeSort } from '../src/algorithms.js';
import { Player, generateArray, mulberry32, PRESETS } from '../src/player.js';

const sortedCopy = (a) => [...a].sort((x, y) => x - y);
const events = (fn, input) => [...fn(input)];

/** Replay an event stream onto a copy of the input, as the UI does. */
function replay(fn, input) {
  return new Player(fn, input).finish();
}

const EDGE_CASES = [
  [], [7], [2, 1], [1, 2], [3, 3, 3], [5, 4, 3, 2, 1], [1, 2, 3, 4, 5],
  [4, 1, 3, 1, 4, 2, 2], [10, -3, 0, 7, -3, 99, 1],
];

for (const [key, { name, fn }] of Object.entries(ALGORITHMS)) {
  test(`${name}: replaying events sorts edge cases`, () => {
    for (const input of EDGE_CASES) {
      const state = replay(fn, input);
      assert.deepEqual(state.values, sortedCopy(input), `input ${JSON.stringify(input)}`);
    }
  });

  test(`${name}: sorts many random arrays of every preset`, () => {
    const rand = mulberry32(1234 + key.length);
    for (const preset of PRESETS) {
      for (let trial = 0; trial < 25; trial++) {
        const n = Math.floor(rand() * 80);
        const input = generateArray(n, preset, rand);
        assert.deepEqual(replay(fn, input).values, sortedCopy(input), `${preset} n=${n}`);
      }
    }
  });

  test(`${name}: marks every index sorted exactly once`, () => {
    const input = generateArray(40, 'random', mulberry32(7));
    const marks = events(fn, input).filter((e) => e.type === 'sorted').map((e) => e.i);
    assert.deepEqual([...marks].sort((a, b) => a - b), [...Array(40).keys()]);
  });

  test(`${name}: does not mutate the caller's array`, () => {
    const input = [3, 1, 2];
    events(fn, input);
    assert.deepEqual(input, [3, 1, 2]);
  });

  test(`${name}: every event references valid indices`, () => {
    const input = generateArray(30, 'few-unique', mulberry32(99));
    for (const e of events(fn, input)) {
      for (const k of ['i', 'j', 'lo', 'hi']) {
        if (k in e) assert.ok(e[k] >= 0 && e[k] < input.length, `${e.type}.${k}=${e[k]}`);
      }
    }
  });
}

test('bubble sort exits after one pass on sorted input', () => {
  const n = 20;
  const compares = events(bubbleSort, [...Array(n).keys()]).filter((e) => e.type === 'compare');
  assert.equal(compares.length, n - 1);
});

test('bubble sort swap count equals the number of inversions', () => {
  const input = [5, 1, 4, 2, 8, 0];
  let inversions = 0;
  for (let i = 0; i < input.length; i++) {
    for (let j = i + 1; j < input.length; j++) if (input[i] > input[j]) inversions++;
  }
  assert.equal(events(bubbleSort, input).filter((e) => e.type === 'swap').length, inversions);
});

test('merge sort only writes, never swaps, and does n·⌈log2 n⌉ writes for n = 2^k', () => {
  const input = generateArray(64, 'random', mulberry32(3));
  const evs = events(mergeSort, input);
  assert.equal(evs.filter((e) => e.type === 'swap').length, 0);
  assert.equal(evs.filter((e) => e.type === 'overwrite').length, 64 * 6);
});

test('quick sort stays near n log n comparisons on already-sorted input (median of three)', () => {
  const n = 512;
  const compares = events(quickSort, [...Array(n).keys()]).filter((e) => e.type === 'compare').length;
  // A naive last-element pivot would need ~n²/2 = 131,072 comparisons here.
  assert.ok(compares < 4 * n * Math.log2(n), `got ${compares}`);
});

test('O(n log n) algorithms beat bubble sort on a large random input', () => {
  const input = generateArray(300, 'random', mulberry32(42));
  const count = (fn) => events(fn, input).filter((e) => e.type === 'compare').length;
  const bubble = count(ALGORITHMS.bubble.fn);
  for (const key of ['merge', 'quick', 'heap']) {
    assert.ok(count(ALGORITHMS[key].fn) < bubble / 5, key);
  }
});
