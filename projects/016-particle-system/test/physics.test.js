import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Particle, ParticlePool, KIND } from '../src/particle.js';
import { gravity, drag, wind, attractor, vortex } from '../src/forces.js';
import { ParticleSystem } from '../src/system.js';
import { mulberry32, clamp, lerp, hsl } from '../src/vec.js';

const close = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) <= eps, `${a} ≉ ${b}`);

/** A system with no built-in forces, for isolated physics checks. */
function bare(opts = {}) {
  const s = new ParticleSystem({ width: 1000, height: 1000, capacity: 64, dt: 0.01, ...opts });
  s.forces = [];
  return s;
}

test('vec helpers', () => {
  assert.equal(clamp(5, 0, 3), 3);
  assert.equal(clamp(-1, 0, 3), 0);
  assert.equal(lerp(10, 20, 0.25), 12.5);
  assert.equal(hsl(-30, 100, 50), 'hsla(330, 100%, 50%, 1)');
  const a = mulberry32(42), b = mulberry32(42);
  for (let i = 0; i < 100; i++) {
    const v = a();
    assert.equal(v, b());
    assert.ok(v >= 0 && v < 1);
  }
});

test('pool hands out unique particles and refuses beyond capacity', () => {
  const pool = new ParticlePool(3);
  const got = [pool.acquire(), pool.acquire(), pool.acquire()];
  assert.equal(new Set(got).size, 3);
  assert.equal(pool.liveCount, 3);
  assert.equal(pool.acquire(), null);
  pool.release(got[1]);
  pool.release(got[1]); // double release is harmless
  assert.equal(pool.liveCount, 2);
  const again = pool.acquire();
  assert.equal(again, got[1]);
  assert.equal(again.age, 0, 'recycled particle is reset');
  assert.throws(() => new ParticlePool(0), RangeError);
  const stranger = Object.assign(new Particle(), { alive: true });
  assert.throws(() => pool.release(stranger), /does not belong/);
});

test('applyForce divides by mass (F = m·a)', () => {
  const p = new Particle();
  p.mass = 4;
  p.applyForce(8, -12);
  assert.equal(p.ax, 2);
  assert.equal(p.ay, -3);
});

test('free fall matches semi-implicit Euler closed form', () => {
  const s = bare();
  s.addForce(gravity(100));
  const p = s.spawn({ x: 0, y: 0, life: 100 });
  const n = 50, dt = s.dt, g = 100;
  for (let i = 0; i < n; i++) s.step();
  // v_n = n·g·dt ; x_n = g·dt²·n(n+1)/2 for velocity-first Euler.
  close(p.vy, n * g * dt);
  close(p.y, g * dt * dt * (n * (n + 1)) / 2);
  close(p.x, 0);
});

test('gravity is mass-independent; wind is not', () => {
  const s = bare();
  s.addForce(gravity(200));
  s.addForce(wind(50, 1e9)); // effectively constant at 0.5·strength
  const light = s.spawn({ mass: 1, life: 10 });
  const heavy = s.spawn({ mass: 5, life: 10 });
  for (let i = 0; i < 20; i++) s.step();
  close(light.vy, heavy.vy);
  assert.ok(light.vx > heavy.vx * 4.9, 'lighter particle is blown further');
});

test('drag decays speed exponentially and never reverses it', () => {
  const s = bare();
  s.addForce(drag(2));
  const p = s.spawn({ vx: 100, life: 100 });
  let prev = p.vx;
  for (let i = 0; i < 200; i++) {
    s.step();
    assert.ok(p.vx < prev && p.vx > 0);
    prev = p.vx;
  }
  // Discrete solution: v·(1 − k·dt)^n
  close(p.vx, 100 * (1 - 2 * 0.01) ** 200, 1e-9);
  // Particle-level drag multiplier of 0 disables it.
  const q = s.spawn({ vx: 50, drag: 0, life: 10 });
  s.step();
  assert.equal(q.vx, 50);
});

test('attractor pulls toward its centre, negative strength repels, radius limits reach', () => {
  const s = bare();
  const pull = s.addForce(attractor(500, 500, 1e5, 10));
  const p = s.spawn({ x: 400, y: 500, life: 10 });
  s.step();
  assert.ok(p.vx > 0 && Math.abs(p.vy) < 1e-12);

  pull.strength = -1e5;
  const q = s.spawn({ x: 400, y: 500, life: 10 });
  s.step();
  assert.ok(q.vx < 0);

  pull.radius = 50;
  const far = s.spawn({ x: 0, y: 0, life: 10 });
  s.step();
  assert.equal(far.vx, 0);
});

test('softening keeps the attractor finite at the centre', () => {
  const s = bare();
  s.addForce(attractor(100, 100, 1e6, 20));
  const p = s.spawn({ x: 100, y: 100, life: 10 });
  s.step();
  assert.ok(Number.isFinite(p.x) && Number.isFinite(p.vx));
});

test('vortex force is perpendicular to the radius', () => {
  const s = bare();
  s.addForce(vortex(0, 0, 1000, 10));
  const p = s.spawn({ x: 100, y: 0, life: 10 });
  p.ax = p.ay = 0;
  s.forces[0].apply(p, 0);
  close(p.ax, 0);
  assert.ok(p.ay > 0, 'counter-clockwise in canvas coordinates');
});

test('disabled forces are skipped', () => {
  const s = bare();
  const g = s.addForce(gravity(500));
  g.enabled = false;
  const p = s.spawn({ life: 10 });
  s.step();
  assert.equal(p.vy, 0);
});

test('particles die at the end of life and are culled off-screen', () => {
  const s = bare();
  s.spawn({ life: 0.05 });
  s.spawn({ x: 500, y: 1100, life: 10 }); // below world + margin
  s.step();
  assert.equal(s.pool.liveCount, 1);
  for (let i = 0; i < 10; i++) s.step();
  assert.equal(s.pool.liveCount, 0);
});

test('trail history is bounded', () => {
  const s = bare();
  const p = s.spawn({ vx: 10, trail: 4, life: 10 });
  for (let i = 0; i < 30; i++) s.step();
  assert.equal(p.history.length, 8);
  assert.ok(p.history[6] < p.x);
});

test('advance() runs fixed steps and carries the remainder', () => {
  const s = bare({ dt: 0.01 });
  let r = s.advance(0.035);
  assert.equal(r.steps, 3);
  close(r.alpha, 0.5);
  r = s.advance(0.005);
  assert.equal(r.steps, 1);
  close(s.time, 0.04);
  // Huge pauses (hidden tab) are capped instead of freezing the page.
  r = s.advance(60);
  assert.equal(r.steps, s.maxStepsPerFrame);
  assert.equal(s.accumulator, 0);
  assert.equal(s.advance(-1).steps, 0);
});

test('frame rate does not change the result (determinism)', () => {
  const run = (frameDt, frames) => {
    const s = new ParticleSystem({ width: 800, height: 600, seed: 7, dt: 1 / 120 });
    s.launch(400, 200, { pattern: 'ring', hue: 120, count: 40 });
    for (let i = 0; i < frames; i++) s.advance(frameDt);
    return s.live().map((p) => [p.x, p.y]);
  };
  const a = run(1 / 60, 120);   // 2 s at 60 fps
  const b = run(1 / 30, 60);    // 2 s at 30 fps
  assert.equal(a.length, b.length);
  for (let i = 0; i < a.length; i++) {
    close(a[i][0], b[i][0], 1e-6);
    close(a[i][1], b[i][1], 1e-6);
  }
});

test('KIND constants are distinct', () => {
  assert.notEqual(KIND.SPARK, KIND.ROCKET);
});
