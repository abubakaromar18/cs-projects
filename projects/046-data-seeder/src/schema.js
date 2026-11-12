/**
 * Schema validation and dependency ordering.
 *
 * A schema looks like:
 *
 *   {
 *     "tables": {
 *       "users": {
 *         "count": 10,
 *         "fields": {
 *           "id":    { "type": "serial", "primaryKey": true },
 *           "email": { "type": "email", "unique": true }
 *         }
 *       },
 *       "posts": {
 *         "count": 30,
 *         "fields": {
 *           "id":      { "type": "serial", "primaryKey": true },
 *           "user_id": { "type": "ref", "table": "users", "column": "id" }
 *         }
 *       }
 *     }
 *   }
 *
 * Foreign keys ("ref" fields) form a directed graph between tables. Parents
 * must be generated before children, so we topologically sort with Kahn's
 * algorithm and report a clear error if a cycle makes that impossible.
 */
import { hasGenerator } from './generators.js';

export class SchemaError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SchemaError';
  }
}

/** Validate a schema object. Throws SchemaError listing every problem found. */
export function validateSchema(schema) {
  const errors = [];
  if (!schema || typeof schema !== 'object' || !schema.tables || typeof schema.tables !== 'object') {
    throw new SchemaError('Schema must be an object with a "tables" object');
  }

  const tables = schema.tables;
  for (const [tName, table] of Object.entries(tables)) {
    if (!Number.isInteger(table.count) || table.count < 0) {
      errors.push(`${tName}: "count" must be a non-negative integer`);
    }
    if (!table.fields || Object.keys(table.fields).length === 0) {
      errors.push(`${tName}: must define at least one field`);
      continue;
    }
    const seen = [];
    for (const [fName, field] of Object.entries(table.fields)) {
      const where = `${tName}.${fName}`;
      if (!field || typeof field.type !== 'string') {
        errors.push(`${where}: missing "type"`);
        continue;
      }
      if (field.type === 'ref') {
        const target = tables[field.table];
        if (!target) {
          errors.push(`${where}: references unknown table "${field.table}"`);
        } else if (!field.column || !target.fields?.[field.column]) {
          errors.push(`${where}: references unknown column "${field.table}.${field.column}"`);
        } else if (field.table === tName && !field.nullable) {
          // The first row of a self-referencing table has nothing to point at.
          errors.push(`${where}: self-reference must be "nullable"`);
        }
      } else if (!hasGenerator(field.type)) {
        errors.push(`${where}: unknown type "${field.type}"`);
      }
      if (field.primaryKey && field.nullable) {
        errors.push(`${where}: a primary key cannot be nullable`);
      }
      if (field.nullRate !== undefined && !(field.nullRate >= 0 && field.nullRate <= 1)) {
        errors.push(`${where}: "nullRate" must be between 0 and 1`);
      }
      // Intra-row dependencies: fields are generated in declaration order.
      const intraDeps = [];
      if (field.after) intraDeps.push(field.after);
      if (field.type === 'slug' && field.from) intraDeps.push(field.from);
      for (const dep of intraDeps) {
        if (!seen.includes(dep)) {
          errors.push(`${where}: depends on "${dep}", which must be declared earlier in the table`);
        }
      }
      seen.push(fName);
    }
  }

  if (errors.length) throw new SchemaError('Invalid schema:\n  - ' + errors.join('\n  - '));
  return true;
}

/** Return the set of tables a given table depends on (excluding itself). */
export function dependenciesOf(table, selfName) {
  const deps = new Set();
  for (const field of Object.values(table.fields)) {
    if (field.type === 'ref' && field.table !== selfName) deps.add(field.table);
  }
  return deps;
}

/**
 * Kahn's algorithm. Returns table names ordered so that every table appears
 * after all tables it references. Ties keep schema declaration order, so the
 * output is stable and predictable.
 */
export function topoSortTables(schema) {
  const names = Object.keys(schema.tables);
  const inDegree = new Map(names.map((n) => [n, 0]));
  const children = new Map(names.map((n) => [n, []]));

  for (const name of names) {
    for (const dep of dependenciesOf(schema.tables[name], name)) {
      inDegree.set(name, inDegree.get(name) + 1);
      children.get(dep).push(name);
    }
  }

  const queue = names.filter((n) => inDegree.get(n) === 0);
  const order = [];
  while (queue.length) {
    const n = queue.shift();
    order.push(n);
    for (const child of children.get(n)) {
      inDegree.set(child, inDegree.get(child) - 1);
      if (inDegree.get(child) === 0) queue.push(child);
    }
  }

  if (order.length !== names.length) {
    const stuck = names.filter((n) => !order.includes(n));
    throw new SchemaError(`Foreign-key cycle detected between tables: ${stuck.join(', ')}`);
  }
  return order;
}
