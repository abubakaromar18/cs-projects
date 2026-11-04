import { test } from 'node:test';
import assert from 'node:assert/strict';
import { HighScores, memoryStorage, STORAGE_KEY, MAX_ENTRIES } from '../src/highscores.js';

test('empty table', () => {
  const hs = new HighScores();
  assert.deepEqual(hs.list(), []);
  assert.equal(hs.best(), 0);
  assert.equal(hs.qualifies(0), false);
  assert.equal(hs.qualifies(1), true);
});

test('scores are sorted descending and ranks returned', () => {
  const hs = new HighScores();
  assert.equal(hs.add({ name: 'a', score: 50 }), 0);
  assert.equal(hs.add({ name: 'b', score: 120 }), 0);
  assert.equal(hs.add({ name: 'c', score: 80 }), 1);
  assert.deepEqual(hs.list().map((e) => e.name), ['b', 'c', 'a']);
  assert.equal(hs.best(), 120);
});

test('table is capped and low scores no longer qualify', () => {
  const hs = new HighScores();
  for (let i = 1; i <= MAX_ENTRIES; i++) hs.add({ name: `p${i}`, score: i * 10 });
  assert.equal(hs.list().length, MAX_ENTRIES);
  assert.equal(hs.qualifies(10), false);
  assert.equal(hs.add({ name: 'low', score: 5 }), -1);
  assert.equal(hs.add({ name: 'mid', score: 55 }), 5);
  assert.equal(hs.list().length, MAX_ENTRIES);
  assert.ok(!hs.list().some((e) => e.score === 10), 'lowest entry evicted');
});

test('ties rank the earlier score first', () => {
  const hs = new HighScores();
  hs.add({ name: 'late', score: 100, date: '2026-02-01T00:00:00.000Z' });
  hs.add({ name: 'early', score: 100, date: '2026-01-01T00:00:00.000Z' });
  assert.deepEqual(hs.list().map((e) => e.name), ['early', 'late']);
});

test('persists across instances sharing storage', () => {
  const store = memoryStorage();
  new HighScores(store).add({ name: 'Omar', score: 300, level: 2 });
  const again = new HighScores(store).list();
  assert.equal(again[0].name, 'Omar');
  assert.equal(again[0].level, 2);
});

test('names are trimmed, truncated and defaulted', () => {
  const hs = new HighScores();
  hs.add({ name: '   ', score: 10 });
  hs.add({ name: 'abcdefghijklmnopqrstuvwxyz', score: 20 });
  const names = hs.list().map((e) => e.name);
  assert.deepEqual(names, ['abcdefghijkl', 'Player']);
});

test('corrupt or tampered storage is ignored safely', () => {
  const store = memoryStorage();
  store.setItem(STORAGE_KEY, '{not json');
  assert.deepEqual(new HighScores(store).list(), []);
  store.setItem(STORAGE_KEY, JSON.stringify({ a: 1 }));
  assert.deepEqual(new HighScores(store).list(), []);
  store.setItem(STORAGE_KEY, JSON.stringify([{ score: 'x' }, { score: -5 }, null, { name: 'ok', score: 7 }]));
  assert.deepEqual(new HighScores(store).list().map((e) => e.name), ['ok']);
});

test('storage that throws on write does not crash', () => {
  const store = memoryStorage();
  store.setItem = () => { throw new Error('QuotaExceeded'); };
  const hs = new HighScores(store);
  assert.doesNotThrow(() => hs.add({ name: 'x', score: 10 }));
});

test('clear empties the table', () => {
  const hs = new HighScores();
  hs.add({ name: 'x', score: 10 });
  hs.clear();
  assert.deepEqual(hs.list(), []);
});
