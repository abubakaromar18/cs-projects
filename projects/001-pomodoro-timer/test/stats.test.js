import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  SessionLog, MemoryStorage, summarize, currentStreak, lastNDays, groupByDay, dayKey,
} from '../src/stats.js';

const MIN = 60_000;
const DAY = 86_400_000;
// Noon local time avoids DST/midnight edge cases in day arithmetic.
const NOW = new Date(2026, 9, 21, 12, 0, 0).getTime();
const work = (at, minutes = 25) => ({ phase: 'work', duration: minutes * MIN, at });

test('dayKey uses the local calendar date', () => {
  assert.equal(dayKey(NOW), '2026-10-21');
});

test('groupByDay ignores breaks and sums focus time', () => {
  const days = groupByDay([
    work(NOW), work(NOW + MIN), { phase: 'shortBreak', duration: 5 * MIN, at: NOW },
  ]);
  assert.deepEqual(days, { '2026-10-21': { sessions: 2, focusMs: 50 * MIN } });
});

test('streak counts consecutive days and tolerates no session yet today', () => {
  const sessions = [work(NOW - DAY), work(NOW - 2 * DAY), work(NOW - 4 * DAY)];
  assert.equal(currentStreak(sessions, NOW), 2);
  assert.equal(currentStreak([...sessions, work(NOW)], NOW), 3);
  assert.equal(currentStreak([work(NOW - 3 * DAY)], NOW), 0);
  assert.equal(currentStreak([], NOW), 0);
});

test('lastNDays returns n entries oldest first, including empty days', () => {
  const days = lastNDays([work(NOW), work(NOW - 2 * DAY)], 3, NOW);
  assert.deepEqual(days.map((d) => d.sessions), [1, 0, 1]);
  assert.equal(days[2].day, '2026-10-21');
});

test('summarize reports today and all-time numbers', () => {
  const s = summarize([work(NOW), work(NOW, 50), work(NOW - DAY)], NOW);
  assert.deepEqual(s, {
    todaySessions: 2, todayFocusMinutes: 75, totalSessions: 3, totalFocusMinutes: 100, streak: 2,
  });
});

test('SessionLog persists across instances via storage', () => {
  const storage = new MemoryStorage();
  const a = new SessionLog(storage);
  a.add(work(NOW));
  const b = new SessionLog(storage);
  assert.equal(b.sessions.length, 1);
  b.clear();
  assert.equal(new SessionLog(storage).sessions.length, 0);
});

test('SessionLog recovers from corrupted or invalid data', () => {
  const storage = new MemoryStorage();
  storage.setItem('pomodoro.sessions.v1', '{not json');
  assert.deepEqual(new SessionLog(storage).sessions, []);
  storage.setItem('pomodoro.sessions.v1', JSON.stringify([work(NOW), { bad: true }]));
  assert.equal(new SessionLog(storage).sessions.length, 1);
});

test('SessionLog survives a storage that throws', () => {
  const throwing = {
    getItem() { throw new Error('blocked'); },
    setItem() { throw new Error('quota'); },
    removeItem() { throw new Error('blocked'); },
  };
  const log = new SessionLog(throwing);
  log.add(work(NOW));
  assert.equal(log.sessions.length, 1);
  assert.doesNotThrow(() => log.clear());
});

test('SessionLog rejects invalid entries', () => {
  const log = new SessionLog(new MemoryStorage());
  assert.throws(() => log.add({ phase: 'work', duration: NaN, at: NOW }), TypeError);
});
