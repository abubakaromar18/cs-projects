import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { csvCell, tableToCSV, sqlLiteral, sqlIdent, toSQL, toJSON } from '../src/formatters.js';
import { seed } from '../src/seeder.js';
import { parseCounts } from '../bin/seed.js';

const CLI = fileURLToPath(new URL('../bin/seed.js', import.meta.url));
const BLOG = fileURLToPath(new URL('../examples/blog.schema.json', import.meta.url));

test('csvCell quotes only when needed (RFC 4180)', () => {
  assert.equal(csvCell('plain'), 'plain');
  assert.equal(csvCell('a,b'), '"a,b"');
  assert.equal(csvCell('say "hi"'), '"say ""hi"""');
  assert.equal(csvCell('line\nbreak'), '"line\nbreak"');
  assert.equal(csvCell(null), '');
  assert.equal(csvCell(3.5), '3.5');
});

test('tableToCSV writes a header and CRLF-terminated rows', () => {
  const csv = tableToCSV([{ a: 1, b: 'x,y' }, { a: 2, b: null }], ['a', 'b']);
  assert.equal(csv, 'a,b\r\n1,"x,y"\r\n2,\r\n');
});

test('sqlLiteral escapes and types values', () => {
  assert.equal(sqlLiteral("O'Brien"), "'O''Brien'");
  assert.equal(sqlLiteral(null), 'NULL');
  assert.equal(sqlLiteral(true), 'TRUE');
  assert.equal(sqlLiteral(42), '42');
  assert.throws(() => sqlLiteral(Infinity));
  assert.equal(sqlIdent('we"ird'), '"we""ird"');
});

test('toSQL emits inserts in dependency order inside a transaction', () => {
  const schema = JSON.parse(readFileSync(BLOG, 'utf8'));
  const sql = toSQL(seed(schema, { seed: 1 }), schema);
  assert.ok(sql.startsWith('BEGIN;') && sql.trimEnd().endsWith('COMMIT;'));
  const pos = (t) => sql.indexOf(`INSERT INTO "${t}"`);
  assert.ok(pos('users') < pos('posts') && pos('posts') < pos('comments'));
});

test('toSQL batches large tables', () => {
  const schema = { tables: { t: { count: 250, fields: { id: { type: 'serial' } } } } };
  const sql = toSQL(seed(schema, { seed: 1 }), schema, { batchSize: 100 });
  assert.equal(sql.match(/INSERT INTO/g).length, 3);
});

test('toJSON round-trips', () => {
  const schema = JSON.parse(readFileSync(BLOG, 'utf8'));
  const result = seed(schema, { seed: 2 });
  assert.deepEqual(JSON.parse(toJSON(result)), result.data);
});

test('parseCounts parses table=n pairs', () => {
  assert.deepEqual(parseCounts(['users=10', 'posts=3']), { users: 10, posts: 3 });
  assert.throws(() => parseCounts(['bad']), /table=n/);
});

test('CLI produces identical JSON for the same seed', () => {
  const run = () => execFileSync(process.execPath, [CLI, BLOG, '--seed', '42'], { encoding: 'utf8' });
  const out = run();
  assert.equal(out, run());
  assert.equal(JSON.parse(out).users.length, 5);
});

test('CLI writes one CSV per table', () => {
  const dir = mkdtempSync(join(tmpdir(), 'seeder-'));
  try {
    execFileSync(process.execPath, [CLI, BLOG, '-f', 'csv', '-o', dir, '-s', '1', '-c', 'users=3'], { stdio: 'pipe' });
    assert.deepEqual(readdirSync(dir).sort(), ['categories.csv', 'comments.csv', 'posts.csv', 'users.csv']);
    const lines = readFileSync(join(dir, 'users.csv'), 'utf8').trim().split('\r\n');
    assert.equal(lines.length, 4); // header + 3
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('CLI exits non-zero on an invalid schema', () => {
  assert.throws(
    () => execFileSync(process.execPath, [CLI, '/nonexistent.json'], { stdio: 'pipe' }),
    (e) => e.status === 1,
  );
});
