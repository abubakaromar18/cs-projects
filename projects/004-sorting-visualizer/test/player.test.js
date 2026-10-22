import { test } from 'node:test';
import assert from 'node:assert/strict';
import { heapSort, quickSort, mergeSort } from '../src/algorithms.js';
import { Player, applyEvent, generateArray, mulberry32, playbackRate, PRESETS } from '../src/player.js';

test('player starts on the unsorted input and counts events by type', () => {
  const p = new Player(heapSort, [3, 1, 2]);
  assert.deepEqual(p.state.values, [3, 1, 2]);
  assert.equal(p.state.done, false);
  const s = p.finish();
  assert.equal(s.done, true);
  assert.deepEqual(s.values, [1, 2, 3]);
  assert.equal(s.stats.steps, s.stats.comparisons + s.stats.swaps + s.stats.writes + s.sorted.size);
});

test('highlights last only for the step that produced them', () => {
  const p = new Player(heapSort, [1, 3, 2]);
  const first = p.step();
  assert.equal(first.type, 'compare');
  assert.deepEqual(p.state.comparing, [first.i, first.j]);
  p.finish();
  assert.deepEqual(p.state.comparing, []);
  assert.deepEqual(p.state.swapping, []);
});

test('step returns null once finished and stepMany reports applied count', () => {
  const p = new Player(mergeSort, [2, 1]);
  const applied = p.stepMany(1000);
  assert.ok(applied > 0 && applied < 1000);
  assert.equal(p.step(), null);
  assert.equal(p.stepMany(5), 0);
});

test('reset rewinds to the original input and zeroes stats', () => {
  const p = new Player(quickSort, [9, 8, 7, 6]);
  p.stepMany(5);
  p.reset();
  assert.deepEqual(p.state.values, [9, 8, 7, 6]);
  assert.equal(p.state.stats.steps, 0);
  assert.deepEqual(p.finish().values, [6, 7, 8, 9]);
});

test('pivot highlight follows the pivot value when it is swapped', () => {
  const s = { values: [5, 1, 9], sorted: new Set(), comparing: [], swapping: [], pivot: 2, range: null,
    stats: { comparisons: 0, swaps: 0, writes: 0, steps: 0 } };
  applyEvent(s, { type: 'swap', i: 0, j: 2 });
  assert.deepEqual(s.values, [9, 1, 5]);
  assert.equal(s.pivot, 0);
  applyEvent(s, { type: 'sorted', i: 0 });
  assert.equal(s.pivot, null);
});

test('applyEvent rejects unknown events', () => {
  assert.throws(() => applyEvent({}, { type: 'teleport' }), /Unknown event/);
});

test('generateArray produces the requested size and shape', () => {
  const rand = mulberry32(5);
  for (const preset of PRESETS) {
    const a = generateArray(50, preset, rand);
    assert.equal(a.length, 50);
    assert.ok(a.every((v) => Number.isInteger(v) && v >= 1 && v <= 100), preset);
  }
  const rev = generateArray(10, 'reversed');
  assert.deepEqual(rev, [...rev].sort((x, y) => y - x));
  assert.ok(new Set(generateArray(100, 'few-unique', rand)).size <= 4);
  assert.deepEqual(generateArray(0), []);
  assert.throws(() => generateArray(-1), RangeError);
  assert.throws(() => generateArray(5, 'zigzag'), /Unknown preset/);
});

test('mulberry32 is deterministic per seed', () => {
  const a = mulberry32(1);
  const b = mulberry32(1);
  const xs = Array.from({ length: 5 }, a);
  assert.deepEqual(xs, Array.from({ length: 5 }, b));
  assert.ok(xs.every((x) => x >= 0 && x < 1));
});

test('playbackRate is monotonic: slower delays at low speed, more steps at high speed', () => {
  assert.deepEqual(playbackRate(1), { delayMs: 500, stepsPerTick: 1 });
  assert.deepEqual(playbackRate(50), { delayMs: 16, stepsPerTick: 1 });
  assert.deepEqual(playbackRate(100), { delayMs: 16, stepsPerTick: 64 });
  assert.deepEqual(playbackRate('junk'), playbackRate(1));
  let prev = playbackRate(1);
  for (let s = 2; s <= 100; s++) {
    const cur = playbackRate(s);
    assert.ok(cur.delayMs <= prev.delayMs && cur.stepsPerTick >= prev.stepsPerTick, `speed ${s}`);
    prev = cur;
  }
});
