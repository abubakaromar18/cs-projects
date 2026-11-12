# 046 · Data Seeder

A zero-dependency Node.js tool that turns a JSON schema description into **realistic,
reproducible fake data** — as JSON, CSV, or SQL `INSERT` statements. It understands
foreign keys (including self-references), unique and primary-key constraints, nullable
columns, and intra-row dependencies like "`updated_at` must come after `created_at`".

```bash
node bin/seed.js examples/blog.schema.json --format sql --seed 42 > seed.sql
```

## Key CS concepts

| Concept | Where |
|---|---|
| **Seeded PRNG** (mulberry32) + string hashing to make output reproducible | `src/rng.js` |
| **Topological sort** (Kahn's algorithm) over the foreign-key graph, with cycle detection | `src/schema.js` |
| **Rejection sampling** with a retry budget and `Set`-based O(1) membership for unique columns | `src/seeder.js` |
| **Weighted sampling** over a cumulative distribution; **Fisher–Yates** shuffle | `src/rng.js` |
| **Strategy registry** — field types are looked up by name, so new types are one entry | `src/generators.js` |
| **Referential integrity by construction** — children only pick values that already exist in the parent | `src/seeder.js` |
| **Escaping / serialization** — RFC 4180 CSV quoting, SQL literal & identifier quoting | `src/formatters.js` |
| UUID v4 bit layout (version & variant nibbles) | `src/generators.js` |

## Project layout

```
bin/seed.js           CLI (node:util parseArgs)
src/rng.js            Seeded Random class
src/words.js          Built-in word lists
src/generators.js     Field type strategies
src/schema.js         Validation + topological ordering
src/seeder.js         Row generation and constraint enforcement
src/formatters.js     JSON / CSV / SQL output
src/index.js          Public API
examples/*.schema.json
test/*.test.js        node:test suites (incl. a real SQLite load test)
```

## Build, run, test

Requires Node.js 18+ (22.5+ to run the SQLite integration test; it is skipped otherwise).
There are no dependencies to install.

```bash
npm test                                              # 53 tests
npm run example                                       # blog schema as SQL, seed 42
node bin/seed.js examples/shop.schema.json -s 7       # JSON to stdout
node bin/seed.js examples/blog.schema.json -f csv -o out/   # one CSV per table
node bin/seed.js examples/blog.schema.json -c users=1000 -c posts=5000 -f sql -o big.sql
node bin/seed.js --list-types
```

As a library:

```js
import { seed, toSQL } from './src/index.js';
const result = seed(schema, { seed: 'demo', counts: { users: 50 } });
console.log(result.order);          // ['users', 'categories', 'posts', 'comments']
console.log(toSQL(result, schema));
```

## Schema format

```json
{
  "tables": {
    "users": {
      "count": 5,
      "fields": {
        "id":         { "type": "serial", "primaryKey": true },
        "first_name": { "type": "firstName" },
        "last_name":  { "type": "lastName" },
        "email":      { "type": "email", "unique": true },
        "role":       { "type": "enum", "values": ["admin", "editor", "reader"], "weights": [1, 3, 10] }
      }
    },
    "posts": {
      "count": 8,
      "fields": {
        "id":           { "type": "uuid", "primaryKey": true },
        "author_id":    { "type": "ref", "table": "users", "column": "id" },
        "title":        { "type": "title" },
        "slug":         { "type": "slug", "from": "title", "unique": true },
        "published_at": { "type": "datetime", "from": "2024-01-01", "to": "2025-06-01" },
        "updated_at":   { "type": "datetime", "after": "published_at" }
      }
    }
  }
}
```

Field options available on every type:

- `unique` / `primaryKey` — no duplicates (primary keys can't be nullable)
- `nullable` + `nullRate` (default 0.2) — fraction of rows that get `NULL`

Fields are generated **in declaration order**, so a field may depend on earlier ones
(`email` reuses `first_name`/`last_name`, `template` can use `{{any_earlier_field}}`,
`slug.from`, `datetime.after`).

**Types:** `serial`, `uuid`, `int`, `float`, `boolean`, `enum`, `constant`, `template`,
`firstName`, `lastName`, `fullName`, `email`, `username`, `phone`, `street`, `city`,
`country`, `zip`, `company`, `productName`, `price`, `word`, `sentence`, `paragraph`,
`title`, `slug`, `datetime`, `date`, `url`, `ipv4`, `hexColor`, and `ref`.

Generated data is safe by design: emails use reserved `example.*` / `.test` domains,
phone numbers use the fictional 555-01xx range, and IPs are in private `10.0.0.0/8`.

## Example output

```sql
BEGIN;

INSERT INTO "users" ("id", "first_name", "last_name", "email", "role", "created_at") VALUES
  (1, 'Tara', 'Patel', 'tara.patel@example.org', 'editor', '2023-10-16T03:14:44.494Z'),
  (2, 'Gabriel', 'Usman', 'gabriel.usman204@example.com', 'reader', '2023-08-25T04:27:32.800Z'),
  (3, 'Aisha', 'Tanaka', 'aisha.tanaka@example.net', 'reader', '2023-03-11T18:59:42.454Z');

INSERT INTO "categories" ("id", "name", "parent_id") VALUES
  (1, 'cillum', NULL),
  (2, 'dolore', NULL),
  (3, 'ullamco', NULL);

INSERT INTO "comments" ("id", "post_id", "user_id", "body") VALUES
  (1, '9997ddef-e2d6-4ffd-b4c6-2741dc137c72', 3, 'Fugiat nulla magna aute deserunt adipiscing.'),
  (2, '4c320b64-a9e6-44a6-b230-f993bddf01b4', 2, 'Labore anim exercitation labore.');

COMMIT;
```

Errors are explicit rather than silent:

```
error: Invalid schema:
  - posts.author_id: references unknown table "user"
  - posts.updated_at: depends on "published_at", which must be declared earlier in the table
error: Foreign-key cycle detected between tables: a, b
error: t.v: could not produce a unique value after 1000 attempts (row 2). The value space is probably smaller than "count".
```

## Possible extensions

- Read schemas straight from a database (`information_schema`) or a Prisma / SQL DDL file
- Emit `CREATE TABLE` DDL alongside the inserts
- Many-to-many join tables with a "unique pair" constraint across two columns
- Distributions beyond uniform (normal, Zipf) for more realistic skew
- Locale packs for names and addresses
- Streaming output for millions of rows without holding everything in memory
- Break FK cycles by inserting with `NULL` first and issuing `UPDATE`s afterwards
