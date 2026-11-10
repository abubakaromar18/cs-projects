import { test } from 'node:test';
import assert from 'node:assert/strict';

import { PasteStore, StoreFullError } from '../src/store.js';
import { generateId, isValidId, ALPHABET } from '../src/ids.js';
import { parseExpiry, describeRemaining } from '../src/expiry.js';
import { highlight, normalizeLanguage, escapeHtml } from '../src/highlight.js';

/** A controllable clock for deterministic expiry tests. */
function fakeClock(start = 1_000_000) {
  let t = start;
  return { now: () => t, advance: (ms) => { t += ms; } };
}

test('ids are base62, the requested length, and unique in practice', () => {
  const seen = new Set();
  for (let i = 0; i < 2000; i++) {
    const id = generateId(8);
    assert.equal(id.length, 8);
    assert.ok([...id].every((c) => ALPHABET.includes(c)));
    assert.ok(isValidId(id));
    seen.add(id);
  }
  assert.equal(seen.size, 2000);
  assert.equal(isValidId('../etc'), false);
  assert.equal(isValidId('ab'), false);
});

test('parseExpiry handles units, never, defaults and rejects garbage', () => {
  assert.equal(parseExpiry('10m'), 600_000);
  assert.equal(parseExpiry('1H'), 3_600_000);
  assert.equal(parseExpiry('2d'), 2 * 86_400_000);
  assert.equal(parseExpiry('never'), null);
  assert.equal(parseExpiry(undefined), 86_400_000);
  assert.throws(() => parseExpiry('soon'), RangeError);
  assert.throws(() => parseExpiry('0m'), RangeError);
  assert.throws(() => parseExpiry('31d'), RangeError);
});

test('describeRemaining produces readable phrases', () => {
  assert.equal(describeRemaining(null), 'never');
  assert.equal(describeRemaining(3 * 3_600_000 + 5, 0), 'in 3 hours');
  assert.equal(describeRemaining(60_000, 0), 'in 1 minute');
});

test('paste is readable before expiry and gone after', () => {
  const clock = fakeClock();
  const store = new PasteStore({ now: clock.now });
  const p = store.create({ content: 'hello', ttlMs: 1000 });

  clock.advance(999);
  assert.equal(store.view(p.id).content, 'hello');

  clock.advance(1);
  assert.equal(store.view(p.id), null, 'expires exactly at the deadline');
  assert.equal(store.size, 0, 'lazy expiry also frees memory');
});

test('sweep evicts only expired pastes, in deadline order', () => {
  const clock = fakeClock();
  const store = new PasteStore({ now: clock.now });
  const a = store.create({ content: 'a', ttlMs: 300 });
  const b = store.create({ content: 'b', ttlMs: 100 });
  const c = store.create({ content: 'c', ttlMs: 200 });
  const forever = store.create({ content: 'forever', ttlMs: null });

  clock.advance(150);
  assert.equal(store.sweep(), 1);
  assert.equal(store.peek(b.id), null);
  assert.ok(store.peek(a.id) && store.peek(c.id));

  clock.advance(1_000_000);
  assert.equal(store.sweep(), 2);
  assert.equal(store.size, 1);
  assert.equal(store.peek(forever.id).content, 'forever');
});

test('sweep ignores stale heap entries for already-deleted pastes', () => {
  const clock = fakeClock();
  const store = new PasteStore({ now: clock.now });
  const p = store.create({ content: 'x', ttlMs: 10 });
  store.delete(p.id);
  clock.advance(20);
  assert.equal(store.sweep(), 0);
});

test('burn-after-read pastes can be viewed exactly once', () => {
  const store = new PasteStore();
  const p = store.create({ content: 'secret', burnAfterRead: true });
  assert.equal(store.peek(p.id).views, 0, 'peek does not burn');
  const first = store.view(p.id);
  assert.equal(first.content, 'secret');
  assert.equal(first.views, 1);
  assert.equal(store.view(p.id), null);
});

test('views are counted and returned objects are copies', () => {
  const store = new PasteStore();
  const p = store.create({ content: 'x' });
  store.view(p.id);
  const v = store.view(p.id);
  assert.equal(v.views, 2);
  v.content = 'mutated';
  assert.equal(store.peek(p.id).content, 'x');
});

test('deleteWithToken requires the right token', () => {
  const store = new PasteStore();
  const p = store.create({ content: 'x' });
  assert.equal(store.deleteWithToken(p.id, 'wrong'), 'forbidden');
  assert.equal(store.deleteWithToken(p.id, undefined), 'forbidden');
  assert.equal(store.deleteWithToken(p.id, p.deleteToken), 'deleted');
  assert.equal(store.deleteWithToken(p.id, p.deleteToken), 'not_found');
});

test('store enforces its capacity, reclaiming expired space first', () => {
  const clock = fakeClock();
  const store = new PasteStore({ now: clock.now, maxPastes: 2 });
  store.create({ content: '1', ttlMs: 10 });
  store.create({ content: '2' });
  assert.throws(() => store.create({ content: '3' }), StoreFullError);
  clock.advance(10);
  assert.doesNotThrow(() => store.create({ content: '3' }));
});

test('recent lists newest public pastes first', () => {
  const clock = fakeClock();
  const store = new PasteStore({ now: clock.now });
  store.create({ content: 'old', title: 'old' });
  clock.advance(1);
  store.create({ content: 'burn', title: 'burn', burnAfterRead: true });
  clock.advance(1);
  store.create({ content: 'new', title: 'new' });
  assert.deepEqual(store.recent().map((p) => p.title), ['new', 'old']);
});

test('highlighting escapes HTML and honours explicit languages', () => {
  const { html, language } = highlight('const x = "<script>";', 'javascript');
  assert.equal(language, 'javascript');
  assert.match(html, /hljs-keyword/);
  assert.ok(!html.includes('<script>'));

  const plain = highlight('<b>hi</b>', 'plaintext');
  assert.equal(plain.html, '&lt;b&gt;hi&lt;/b&gt;');

  const auto = highlight('def f(x):\n    return x * 2\n', 'auto');
  assert.equal(auto.language, 'python');
});

test('normalizeLanguage maps unknowns to auto', () => {
  assert.equal(normalizeLanguage('Python'), 'python');
  assert.equal(normalizeLanguage('text'), 'plaintext');
  assert.equal(normalizeLanguage('klingon'), 'auto');
  assert.equal(normalizeLanguage(undefined), 'auto');
  assert.equal(escapeHtml(`"'&`), '&quot;&#39;&amp;');
});
