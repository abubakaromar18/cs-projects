/**
 * Output formatters: JSON, CSV (RFC 4180), and SQL INSERT statements.
 * Each takes the `{ order, data }` result from seed().
 */

export function toJSON(result, { pretty = true } = {}) {
  return JSON.stringify(result.data, null, pretty ? 2 : 0) + '\n';
}

/** Quote a CSV cell per RFC 4180: wrap in quotes if it has , " CR or LF. */
export function csvCell(value) {
  if (value === null || value === undefined) return '';
  const s = String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** CSV for a single table (header row + data rows, CRLF line endings). */
export function tableToCSV(rows, columns) {
  const cols = columns ?? (rows[0] ? Object.keys(rows[0]) : []);
  const lines = [cols.map(csvCell).join(',')];
  for (const row of rows) lines.push(cols.map((c) => csvCell(row[c])).join(','));
  return lines.join('\r\n') + '\r\n';
}

/** Returns a map of table name -> CSV text, one file per table. */
export function toCSV(result, schema) {
  const out = {};
  for (const name of result.order) {
    out[name] = tableToCSV(result.data[name], Object.keys(schema.tables[name].fields));
  }
  return out;
}

/** Quote an SQL identifier with double quotes (ANSI / PostgreSQL / SQLite). */
export function sqlIdent(name) {
  return `"${String(name).replace(/"/g, '""')}"`;
}

/**
 * Render a JS value as an SQL literal. Strings are single-quoted with
 * embedded quotes doubled — the standard escape that prevents the generated
 * script from breaking (or injecting) on values like O'Brien.
 */
export function sqlLiteral(value) {
  if (value === null || value === undefined) return 'NULL';
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error(`Cannot render non-finite number ${value} as SQL`);
    return String(value);
  }
  return `'${String(value).replace(/'/g, "''")}'`;
}

/**
 * SQL script with multi-row INSERTs in dependency order, batched so very
 * large tables don't create one giant statement. Wrapped in a transaction.
 */
export function toSQL(result, schema, { batchSize = 100 } = {}) {
  const parts = ['BEGIN;'];
  for (const name of result.order) {
    const rows = result.data[name];
    if (rows.length === 0) continue;
    const cols = Object.keys(schema.tables[name].fields);
    const header = `INSERT INTO ${sqlIdent(name)} (${cols.map(sqlIdent).join(', ')}) VALUES`;
    for (let i = 0; i < rows.length; i += batchSize) {
      const values = rows
        .slice(i, i + batchSize)
        .map((r) => `  (${cols.map((c) => sqlLiteral(r[c])).join(', ')})`)
        .join(',\n');
      parts.push(`${header}\n${values};`);
    }
  }
  parts.push('COMMIT;');
  return parts.join('\n\n') + '\n';
}
