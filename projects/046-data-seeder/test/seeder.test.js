import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { seed, SeedError } from '../src/seeder.js';

const blog = JSON.parse(readFileSync(new URL('../examples/blog.schema.json', import.meta.url)));
const shop = JSON.parse(readFileSync(new URL('../examples/shop.schema.json', import.meta.url)));

test('generates the requested number of rows per table', () => {
  const { data } = seed(blog, { seed: 1 });
  for (const [name, table] of Object.entries(blog.tables)) assert.equal(data[name].length, table.count, name);
});

test('is deterministic for a given seed', () => {
  assert.deepEqual(seed(blog, { seed: 'repeat' }), seed(blog, { seed: 'repeat' }));
  assert.notDeepEqual(seed(blog, { seed: 'a' }).data, seed(blog, { seed: 'b' }).data);
});

test('every foreign key points at an existing parent row', () => {
  for (const s of [1, 2, 3, 4, 5]) {
    const { data } = seed(blog, { seed: s, counts: { posts: 40, comments: 100 } });
    const userIds = new Set(data.users.map((u) => u.id));
    const postIds = new Set(data.posts.map((p) => p.id));
    const catIds = new Set(data.categories.map((c) => c.id));
    for (const p of data.posts) {
      assert.ok(userIds.has(p.author_id));
      assert.ok(catIds.has(p.category_id));
    }
    for (const c of data.comments) {
      assert.ok(postIds.has(c.post_id));
      assert.ok(c.user_id === null || userIds.has(c.user_id));
    }
  }
});

test('self-references only point at earlier rows', () => {
  const { data } = seed(blog, { seed: 11, counts: { categories: 30 } });
  data.categories.forEach((c, i) => {
    if (c.parent_id !== null) assert.ok(c.parent_id < c.id, `row ${i}`);
  });
  assert.equal(data.categories[0].parent_id, null);
});

test('unique and primary-key columns contain no duplicates', () => {
  const { data } = seed(shop, { seed: 3, counts: { customers: 200, orders: 300 } });
  const emails = data.customers.map((c) => c.email);
  assert.equal(new Set(emails).size, emails.length);
  const ids = data.orders.map((o) => o.id);
  assert.equal(new Set(ids).size, ids.length);
});

test('nullRate controls how often nullable columns are null', () => {
  const schema = {
    tables: { t: { count: 4000, fields: { v: { type: 'int', nullable: true, nullRate: 0.3 } } } },
  };
  const nulls = seed(schema, { seed: 8 }).data.t.filter((r) => r.v === null).length;
  assert.ok(nulls > 1000 && nulls < 1400, `got ${nulls}`);
});

test('fails clearly when a unique value space is exhausted', () => {
  const schema = {
    tables: { t: { count: 5, fields: { v: { type: 'enum', values: ['a', 'b'], unique: true } } } },
  };
  assert.throws(() => seed(schema, { seed: 1, maxAttempts: 50 }), SeedError);
  assert.throws(() => seed(schema, { seed: 1, maxAttempts: 50 }), /t\.v: could not produce a unique value/);
});

test('fails clearly when a required parent table is empty', () => {
  const schema = {
    tables: {
      p: { count: 0, fields: { id: { type: 'serial' } } },
      c: { count: 1, fields: { p_id: { type: 'ref', table: 'p', column: 'id' } } },
    },
  };
  assert.throws(() => seed(schema, { seed: 1 }), /parent table has no rows/);
});

test('count overrides take precedence over the schema', () => {
  const { data } = seed(shop, { seed: 1, counts: { products: 2 } });
  assert.equal(data.products.length, 2);
});

test('updated_at is never before published_at', () => {
  const { data } = seed(blog, { seed: 21, counts: { posts: 200 } });
  for (const p of data.posts) assert.ok(p.updated_at >= p.published_at);
});

test('template fields combine earlier columns', () => {
  const { data } = seed(shop, { seed: 4 });
  for (const c of data.customers) assert.equal(c.display_name, `${c.first_name} ${c.last_name}`);
  assert.deepEqual(data.products.map((p) => p.sku), ['SKU-0', 'SKU-1', 'SKU-2', 'SKU-3', 'SKU-4', 'SKU-5']);
});
