import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateSchema, topoSortTables, SchemaError } from '../src/schema.js';

const t = (fields, count = 1) => ({ count, fields });

test('accepts a valid schema', () => {
  assert.ok(validateSchema({ tables: { a: t({ id: { type: 'serial' } }) } }));
});

test('rejects structural problems and collects every error', () => {
  const schema = {
    tables: {
      a: { count: -1, fields: { x: { type: 'nope' }, y: {} } },
      b: t({ r: { type: 'ref', table: 'zzz', column: 'id' } }),
    },
  };
  assert.throws(
    () => validateSchema(schema),
    (e) => {
      assert.ok(e instanceof SchemaError);
      assert.match(e.message, /count/);
      assert.match(e.message, /unknown type "nope"/);
      assert.match(e.message, /missing "type"/);
      assert.match(e.message, /unknown table "zzz"/);
      return true;
    },
  );
});

test('rejects refs to unknown columns', () => {
  const schema = { tables: { a: t({ id: { type: 'serial' } }), b: t({ a_id: { type: 'ref', table: 'a', column: 'nope' } }) } };
  assert.throws(() => validateSchema(schema), /unknown column "a.nope"/);
});

test('self-references must be nullable', () => {
  const schema = { tables: { a: t({ id: { type: 'serial' }, p: { type: 'ref', table: 'a', column: 'id' } }) } };
  assert.throws(() => validateSchema(schema), /self-reference/);
});

test('"after" must point at an earlier field', () => {
  const schema = { tables: { a: t({ u: { type: 'datetime', after: 'c' }, c: { type: 'datetime' } }) } };
  assert.throws(() => validateSchema(schema), /declared earlier/);
});

test('primary keys cannot be nullable', () => {
  const schema = { tables: { a: t({ id: { type: 'serial', primaryKey: true, nullable: true } }) } };
  assert.throws(() => validateSchema(schema), /primary key/);
});

test('topological sort puts parents before children', () => {
  const schema = {
    tables: {
      comments: t({ post: { type: 'ref', table: 'posts', column: 'id' }, user: { type: 'ref', table: 'users', column: 'id' } }),
      posts: t({ id: { type: 'serial' }, user: { type: 'ref', table: 'users', column: 'id' } }),
      users: t({ id: { type: 'serial' } }),
    },
  };
  const order = topoSortTables(schema);
  assert.deepEqual(order, ['users', 'posts', 'comments']);
});

test('topological sort keeps declaration order for independent tables', () => {
  const schema = { tables: { z: t({ id: { type: 'serial' } }), a: t({ id: { type: 'serial' } }) } };
  assert.deepEqual(topoSortTables(schema), ['z', 'a']);
});

test('self-references do not count as cycles', () => {
  const schema = { tables: { a: t({ id: { type: 'serial' }, p: { type: 'ref', table: 'a', column: 'id', nullable: true } }) } };
  assert.deepEqual(topoSortTables(schema), ['a']);
});

test('detects foreign-key cycles', () => {
  const schema = {
    tables: {
      a: t({ id: { type: 'serial' }, b: { type: 'ref', table: 'b', column: 'id' } }),
      b: t({ id: { type: 'serial' }, a: { type: 'ref', table: 'a', column: 'id' } }),
    },
  };
  assert.throws(() => topoSortTables(schema), /cycle.*a, b/);
});
