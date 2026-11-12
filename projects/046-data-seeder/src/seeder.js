/**
 * The seeding engine.
 *
 * Responsibilities:
 *   1. Validate the schema and order tables by foreign-key dependencies.
 *   2. Generate rows field-by-field, in declaration order.
 *   3. Enforce constraints:
 *        - nullable / nullRate  -> some values become null
 *        - unique / primaryKey  -> rejection sampling with a retry budget
 *        - ref                  -> value drawn from an already-generated parent
 *          column, so every foreign key is satisfiable by construction.
 */
import { Random } from './rng.js';
import { GENERATORS } from './generators.js';
import { validateSchema, topoSortTables } from './schema.js';

export class SeedError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SeedError';
  }
}

const DEFAULT_NULL_RATE = 0.2;
const DEFAULT_MAX_ATTEMPTS = 1000;

/**
 * Generate data for every table in `schema`.
 *
 * @param {object} schema
 * @param {object} [options]
 * @param {number|string} [options.seed]       Seed for reproducible output.
 * @param {object} [options.counts]            Per-table count overrides.
 * @param {number} [options.maxAttempts]       Retry budget for unique fields.
 * @returns {{ order: string[], data: Record<string, object[]> }}
 */
export function seed(schema, options = {}) {
  validateSchema(schema);
  const order = topoSortTables(schema);
  const rng = new Random(options.seed ?? Date.now());
  const maxAttempts = options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS;
  const data = {};

  for (const tableName of order) {
    const table = schema.tables[tableName];
    const count = options.counts?.[tableName] ?? table.count;
    data[tableName] = generateTable(tableName, table, count, { rng, data, maxAttempts });
  }

  return { order, data };
}

function generateTable(tableName, table, count, env) {
  const rows = [];
  // One Set per unique column: O(1) membership checks during rejection sampling.
  const uniqueSets = {};
  for (const [fName, f] of Object.entries(table.fields)) {
    if (f.unique || f.primaryKey) uniqueSets[fName] = new Set();
  }

  for (let index = 0; index < count; index++) {
    const row = {};
    for (const [fName, field] of Object.entries(table.fields)) {
      row[fName] = generateField(fName, field, { tableName, row, index, rows, uniqueSets, ...env });
    }
    rows.push(row);
  }
  return rows;
}

function generateField(fName, field, ctx) {
  const { rng, tableName, uniqueSets, maxAttempts } = ctx;
  const where = `${tableName}.${fName}`;

  // Nullable columns are null with probability nullRate. Unique columns may
  // still be null multiple times (SQL semantics: NULL is never equal to NULL).
  if (field.nullable) {
    const rate = field.nullRate ?? DEFAULT_NULL_RATE;
    if (rng.chance(rate)) return null;
  }

  const produce = field.type === 'ref' ? () => pickReference(field, ctx) : () => runGenerator(field, ctx);

  const set = uniqueSets[fName];
  if (!set) return produce();

  // Rejection sampling: draw until we find an unused value. If the value space
  // is too small for the requested row count we fail loudly instead of looping.
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const value = produce();
    if (value === null) return null;
    const key = typeof value === 'object' ? JSON.stringify(value) : value;
    if (!set.has(key)) {
      set.add(key);
      return value;
    }
  }
  throw new SeedError(
    `${where}: could not produce a unique value after ${maxAttempts} attempts ` +
      `(row ${ctx.index}). The value space is probably smaller than "count".`,
  );
}

function runGenerator(field, ctx) {
  const gen = GENERATORS[field.type];
  return gen(ctx.rng, field, { row: ctx.row, index: ctx.index, table: ctx.tableName });
}

/**
 * Pick a foreign-key value from the referenced table's column.
 * For self-references we can only point at rows generated so far.
 */
function pickReference(field, ctx) {
  const parentRows = field.table === ctx.tableName ? ctx.rows : ctx.data[field.table];
  const candidates = parentRows.map((r) => r[field.column]).filter((v) => v !== null);
  if (candidates.length === 0) {
    if (field.nullable) return null;
    throw new SeedError(
      `${ctx.tableName}: cannot reference "${field.table}.${field.column}" — the parent table has no rows`,
    );
  }
  return ctx.rng.pick(candidates);
}
