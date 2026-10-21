import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  PomodoroTimer, Phase, Status, formatTime, nextPhase, normalizeSettings, DEFAULT_SETTINGS,
} from '../src/timer.js';

const MIN = 60_000;

/** A controllable clock for deterministic tests. */
function fakeClock(start = 1_000_000) {
  let t = start;
  return { now: () => t, advance: (ms) => { t += ms; } };
}

test('formatTime pads and rounds up partial seconds', () => {
  assert.equal(formatTime(25 * MIN), '25:00');
  assert.equal(formatTime(61_000), '01:01');
  assert.equal(formatTime(59_001), '01:00');
  assert.equal(formatTime(0), '00:00');
  assert.equal(formatTime(-500), '00:00');
});

test('normalizeSettings clamps and falls back to defaults', () => {
  const s = normalizeSettings({ workMinutes: 0, shortBreakMinutes: 'abc', longBreakInterval: 99 });
  assert.equal(s.workMinutes, 1);
  assert.equal(s.shortBreakMinutes, DEFAULT_SETTINGS.shortBreakMinutes);
  assert.equal(s.longBreakInterval, 12);
  assert.equal(normalizeSettings({ workMinutes: '30' }).workMinutes, 30);
});

test('nextPhase gives a long break every N work sessions', () => {
  const s = normalizeSettings();
  assert.equal(nextPhase(Phase.WORK, 1, s), Phase.SHORT_BREAK);
  assert.equal(nextPhase(Phase.WORK, 3, s), Phase.SHORT_BREAK);
  assert.equal(nextPhase(Phase.WORK, 4, s), Phase.LONG_BREAK);
  assert.equal(nextPhase(Phase.SHORT_BREAK, 2, s), Phase.WORK);
  assert.equal(nextPhase(Phase.LONG_BREAK, 4, s), Phase.WORK);
});

test('counts down from wall-clock time, not from ticks', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  t.start();
  clock.advance(10 * MIN); // no tick() calls at all in between
  assert.equal(t.getRemaining(), 15 * MIN);
  assert.ok(Math.abs(t.getProgress() - 0.4) < 1e-9);
});

test('pause freezes remaining time and resume continues', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  t.start();
  clock.advance(5 * MIN);
  t.pause();
  assert.equal(t.status, Status.PAUSED);
  clock.advance(60 * MIN);
  assert.equal(t.getRemaining(), 20 * MIN);
  t.start();
  clock.advance(1 * MIN);
  assert.equal(t.getRemaining(), 19 * MIN);
});

test('completing a work session emits complete and moves to a short break', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  const events = [];
  t.on('complete', (e) => events.push(e));
  t.start();
  clock.advance(25 * MIN);
  t.tick();
  assert.equal(events.length, 1);
  assert.equal(events[0].phase, Phase.WORK);
  assert.equal(events[0].duration, 25 * MIN);
  assert.equal(t.phase, Phase.SHORT_BREAK);
  assert.equal(t.status, Status.IDLE);
  assert.equal(t.getRemaining(), 5 * MIN);
  assert.equal(t.completedWork, 1);
});

test('full cycle reaches a long break after 4 sessions, then resets the cycle', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  const run = () => { t.start(); clock.advance(t.getRemaining()); t.tick(); };
  const phases = [];
  for (let i = 0; i < 8; i++) { run(); phases.push(t.phase); }
  assert.deepEqual(phases, [
    'shortBreak', 'work', 'shortBreak', 'work', 'shortBreak', 'work', 'longBreak', 'work',
  ]);
  assert.equal(t.completedWork, 0);
});

test('skip moves on without recording a completion', () => {
  const t = new PomodoroTimer({ now: fakeClock().now });
  let completes = 0;
  t.on('complete', () => completes++);
  t.start();
  t.skip();
  assert.equal(completes, 0);
  assert.equal(t.phase, Phase.SHORT_BREAK);
  assert.equal(t.completedWork, 0);
});

test('reset restores the full phase length', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  t.start();
  clock.advance(7 * MIN);
  t.reset();
  assert.equal(t.status, Status.IDLE);
  assert.equal(t.getRemaining(), 25 * MIN);
});

test('autoStartNext starts the following phase immediately', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now, settings: { autoStartNext: true } });
  t.start();
  clock.advance(25 * MIN);
  t.tick();
  assert.equal(t.phase, Phase.SHORT_BREAK);
  assert.equal(t.status, Status.RUNNING);
  clock.advance(2 * MIN);
  assert.equal(t.getRemaining(), 3 * MIN);
});

test('updateSettings applies to an idle timer but not a running one', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  t.updateSettings({ workMinutes: 50 });
  assert.equal(t.getRemaining(), 50 * MIN);
  t.start();
  clock.advance(MIN);
  t.updateSettings({ workMinutes: 10 });
  assert.equal(t.getRemaining(), 49 * MIN);
});

test('tick emits tick events while running and nothing when idle', () => {
  const clock = fakeClock();
  const t = new PomodoroTimer({ now: clock.now });
  let ticks = 0;
  t.on('tick', () => ticks++);
  t.tick();
  assert.equal(ticks, 0);
  t.start();
  clock.advance(1000);
  t.tick();
  assert.equal(ticks, 1);
});

test('on() returns an unsubscribe function', () => {
  const t = new PomodoroTimer({ now: fakeClock().now });
  let n = 0;
  const off = t.on('change', () => n++);
  t.start();
  off();
  t.pause();
  assert.equal(n, 1);
});
