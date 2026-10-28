import { test } from 'node:test';
import assert from 'node:assert/strict';
import { burst, launchSpeedFor, PATTERN_NAMES } from '../src/fireworks.js';
import { ParticleSystem } from '../src/system.js';
import { KIND } from '../src/particle.js';
import { mulberry32 } from '../src/vec.js';

test('every pattern produces the requested number of finite velocities', () => {
  for (const name of PATTERN_NAMES) {
    for (const count of [0, 1, 60, 200]) {
      const v = burst(name, mulberry32(3), count, 250);
      assert.equal(v.length, count, name);
      for (const s of v) assert.ok(Number.isFinite(s.vx) && Number.isFinite(s.vy), name);
    }
  }
});

test('ring sparks share one speed; peony speeds stay within bounds', () => {
  const ring = burst('ring', mulberry32(1), 90, 200);
  // Ring may be vertically tilted, but horizontal extremes travel at full speed.
  const maxVx = Math.max(...ring.map((s) => Math.abs(s.vx)));
  assert.ok(Math.abs(maxVx - 200) < 1e-9);
  for (const s of burst('peony', mulberry32(1), 200, 200)) {
    assert.ok(Math.hypot(s.vx, s.vy) <= 200 + 1e-9);
  }
});

test('heart is left/right symmetric and upright', () => {
  const v = burst('heart', mulberry32(1), 100, 100);
  const sumX = v.reduce((a, s) => a + s.vx, 0);
  assert.ok(Math.abs(sumX) < 1e-6, 'symmetric around the vertical axis');
  // t = 0 is the top cusp of the heart, which should move upward (negative y).
  assert.ok(v[0].vy < 0);
});

test('willow sparks override life, drag and trail', () => {
  for (const s of burst('willow', mulberry32(9), 20, 200)) {
    assert.ok(s.life > 2 && s.drag > 1 && s.trail > 0);
  }
});

test('burst validates input', () => {
  assert.throws(() => burst('nope', mulberry32(1)), /unknown pattern/);
  assert.throws(() => burst('peony', mulberry32(1), -1), RangeError);
});

test('launchSpeedFor gives v = √(2gh), negative for canvas y-down', () => {
  assert.equal(launchSpeedFor(450, 100), -300);
  assert.equal(launchSpeedFor(0, 100), 0);
  assert.equal(launchSpeedFor(100, 0), 0);
});

test('a rocket climbs to roughly its target and bursts into sparks', () => {
  const s = new ParticleSystem({ width: 800, height: 600, seed: 11, dt: 1 / 240 });
  s.findForce('drag').k = 0;
  let boom = null;
  s.onExplode = (e) => { boom = e; };
  const rocket = s.launch(400, 200, { pattern: 'peony', hue: 30, count: 80 });
  assert.equal(rocket.kind, KIND.ROCKET);
  assert.ok(rocket.vy < 0);

  let minY = Infinity;
  while (!boom && s.time < 5) {
    if (rocket.alive) minY = Math.min(minY, rocket.y);
    s.step();
  }
  assert.ok(boom, 'rocket exploded');
  assert.equal(boom.pattern, 'peony');
  assert.ok(Math.abs(minY - 200) < 10, `apex ${minY} near target 200`);
  assert.equal(s.stats.explosions, 1);
  const sparks = s.live().filter((p) => p.kind === KIND.SPARK);
  assert.equal(sparks.length, 80);
  assert.ok(sparks.every((p) => p.hue >= 30 - 12 && p.hue <= 30 + 12));
});

test('random pattern selection is reproducible from the seed', () => {
  const pick = () => {
    const s = new ParticleSystem({ seed: 99 });
    return Array.from({ length: 8 }, () => s.launch(100, 100).payload.pattern);
  };
  assert.deepEqual(pick(), pick());
});

test('a full show runs, stays within capacity, and drains completely', () => {
  const s = new ParticleSystem({ width: 800, height: 600, capacity: 500, seed: 5 });
  for (let i = 0; i < 10; i++) s.launch(80 * i + 40, 150, { count: 150 });
  let peak = 0;
  for (let i = 0; i < 1200; i++) {   // 10 s at 120 Hz
    s.step();
    peak = Math.max(peak, s.pool.liveCount);
  }
  assert.ok(peak <= 500);
  assert.ok(s.stats.dropped > 0, 'excess spawns were dropped, not allocated');
  assert.equal(s.stats.explosions, 10);
  assert.equal(s.pool.liveCount, 0);
  assert.equal(s.kineticEnergy(), 0);
});

test('clear() kills everything', () => {
  const s = new ParticleSystem({ seed: 2 });
  s.explode(100, 100, { count: 50 });
  assert.equal(s.pool.liveCount, 50);
  assert.ok(s.kineticEnergy() > 0);
  s.clear();
  assert.equal(s.pool.liveCount, 0);
});
