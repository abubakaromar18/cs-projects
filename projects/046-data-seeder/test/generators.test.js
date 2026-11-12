import { test } from 'node:test';
import assert from 'node:assert/strict';
import { GENERATORS } from '../src/generators.js';
import { Random } from '../src/rng.js';

const ctx = (row = {}, index = 0) => ({ row, index, table: 't' });

test('uuid() is a valid v4 UUID', () => {
  const r = new Random(1);
  for (let i = 0; i < 50; i++) {
    assert.match(GENERATORS.uuid(r, {}, ctx()), /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  }
});

test('serial() counts from start', () => {
  assert.equal(GENERATORS.serial(null, {}, ctx({}, 0)), 1);
  assert.equal(GENERATORS.serial(null, { start: 100 }, ctx({}, 4)), 104);
});

test('email() reuses names already in the row', () => {
  const email = GENERATORS.email(new Random(2), {}, ctx({ first_name: 'Mary Ann', last_name: "O'Neil" }));
  assert.match(email, /^mary\.ann\.o\.neil\d*@[\w.]+$/);
});

test('email() honours a fixed domain', () => {
  assert.ok(GENERATORS.email(new Random(2), { domain: 'corp.test' }, ctx()).endsWith('@corp.test'));
});

test('phone() uses the reserved 555-01xx range', () => {
  assert.match(GENERATORS.phone(new Random(3), {}, ctx()), /^\+1-\d{3}-555-01\d{2}$/);
});

test('ipv4() only yields private 10.x addresses', () => {
  assert.match(GENERATORS.ipv4(new Random(3), {}, ctx()), /^10\.\d+\.\d+\.\d+$/);
});

test('enum() requires values and respects them', () => {
  assert.throws(() => GENERATORS.enum(new Random(1), {}, ctx()), /values/);
  const v = GENERATORS.enum(new Random(1), { values: ['x', 'y'] }, ctx());
  assert.ok(['x', 'y'].includes(v));
});

test('template() substitutes earlier fields and index', () => {
  const out = GENERATORS.template(null, { pattern: '{{a}}-{{ b }}-{{index}}' }, ctx({ a: 1, b: 'two' }, 7));
  assert.equal(out, '1-two-7');
  assert.throws(() => GENERATORS.template(null, { pattern: '{{missing}}' }, ctx()), /missing/);
});

test('datetime() stays within range and honours "after"', () => {
  const r = new Random(5);
  const opts = { from: '2024-01-01', to: '2024-02-01' };
  for (let i = 0; i < 100; i++) {
    const d = new Date(GENERATORS.datetime(r, opts, ctx()));
    assert.ok(d >= new Date('2024-01-01') && d <= new Date('2024-02-01'));
  }
  const row = { created: '2024-01-25T00:00:00.000Z' };
  for (let i = 0; i < 50; i++) {
    const d = GENERATORS.datetime(r, { ...opts, after: 'created' }, ctx(row));
    assert.ok(d >= row.created, `${d} < ${row.created}`);
  }
});

test('date() returns YYYY-MM-DD', () => {
  assert.match(GENERATORS.date(new Random(1), {}, ctx()), /^\d{4}-\d{2}-\d{2}$/);
});

test('slug() derives from another field', () => {
  assert.equal(GENERATORS.slug(new Random(1), { from: 'title' }, ctx({ title: 'Hello, World Again!' })), 'hello-world-again');
});

test('sentence() is capitalised and ends with a period', () => {
  const s = GENERATORS.sentence(new Random(9), {}, ctx());
  assert.match(s, /^[A-Z][a-z ]+\.$/);
});

test('price() has at most two decimals and respects bounds', () => {
  const r = new Random(4);
  for (let i = 0; i < 200; i++) {
    const p = GENERATORS.price(r, { min: 5, max: 10 }, ctx());
    assert.ok(p >= 5 && p <= 10);
    assert.equal(Math.round(p * 100) / 100, p);
  }
});
