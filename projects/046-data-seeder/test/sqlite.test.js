// Integration test: load the generated SQL into a real SQLite database with
// foreign keys and UNIQUE constraints enforced. Uses the built-in node:sqlite
// module (Node 22.5+); skipped automatically on older Node versions.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { seed } from '../src/seeder.js';
import { toSQL } from '../src/formatters.js';

let DatabaseSync;
try {
  ({ DatabaseSync } = await import('node:sqlite'));
} catch {
  DatabaseSync = null;
}

const DDL = `
PRAGMA foreign_keys = ON;
CREATE TABLE users (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT UNIQUE NOT NULL, role TEXT, created_at TEXT);
CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE, parent_id INTEGER REFERENCES categories(id));
CREATE TABLE posts (id TEXT PRIMARY KEY, author_id INTEGER NOT NULL REFERENCES users(id), category_id INTEGER NOT NULL REFERENCES categories(id),
                    title TEXT, slug TEXT UNIQUE, body TEXT, published BOOLEAN, published_at TEXT, updated_at TEXT);
CREATE TABLE comments (id INTEGER PRIMARY KEY, post_id TEXT NOT NULL REFERENCES posts(id), user_id INTEGER REFERENCES users(id), body TEXT);
`;

test('generated SQL loads into SQLite with constraints enforced', { skip: !DatabaseSync && 'node:sqlite unavailable' }, () => {
  const schema = JSON.parse(readFileSync(new URL('../examples/blog.schema.json', import.meta.url)));
  const result = seed(schema, { seed: 'sqlite', counts: { users: 30, posts: 80, comments: 200 } });
  const db = new DatabaseSync(':memory:');
  db.exec(DDL);
  db.exec(toSQL(result, schema, { batchSize: 25 }));
  assert.equal(db.prepare('SELECT count(*) AS n FROM comments').get().n, 200);
  assert.deepEqual(db.prepare('PRAGMA foreign_key_check').all(), []);
  db.close();
});
