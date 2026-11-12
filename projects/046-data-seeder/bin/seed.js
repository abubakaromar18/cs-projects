#!/usr/bin/env node
/**
 * CLI: data-seeder <schema.json> [options]
 *
 *   -f, --format <json|csv|sql>   Output format (default: json)
 *   -s, --seed <value>            Seed for reproducible output
 *   -o, --out <path>              File (json/sql) or directory (csv). Default: stdout
 *   -c, --count <table=n>         Override a table's row count (repeatable)
 *       --list-types              Print available field types and exit
 *   -h, --help                    Show help
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { seed, toJSON, toCSV, toSQL, GENERATORS } from '../src/index.js';

const HELP = `Usage: data-seeder <schema.json> [options]

Options:
  -f, --format <json|csv|sql>  Output format (default: json)
  -s, --seed <value>           Seed for reproducible output
  -o, --out <path>             Output file (json/sql) or directory (csv)
  -c, --count <table=n>        Override a table's row count (repeatable)
      --list-types             List available field types
  -h, --help                   Show this help
`;

export function parseCounts(list = []) {
  const counts = {};
  for (const item of list) {
    const m = /^([\w-]+)=(\d+)$/.exec(item);
    if (!m) throw new Error(`Invalid --count "${item}" (expected table=n)`);
    counts[m[1]] = Number(m[2]);
  }
  return counts;
}

function main(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      format: { type: 'string', short: 'f', default: 'json' },
      seed: { type: 'string', short: 's' },
      out: { type: 'string', short: 'o' },
      count: { type: 'string', short: 'c', multiple: true },
      'list-types': { type: 'boolean' },
      help: { type: 'boolean', short: 'h' },
    },
  });

  if (values.help) return void process.stdout.write(HELP);
  if (values['list-types']) {
    return void process.stdout.write(['ref', ...Object.keys(GENERATORS)].sort().join('\n') + '\n');
  }
  if (positionals.length !== 1) {
    process.stderr.write(HELP);
    process.exitCode = 2;
    return;
  }

  const schema = JSON.parse(readFileSync(positionals[0], 'utf8'));
  const result = seed(schema, { seed: values.seed, counts: parseCounts(values.count) });

  switch (values.format) {
    case 'json':
      emit(toJSON(result), values.out);
      break;
    case 'sql':
      emit(toSQL(result, schema), values.out);
      break;
    case 'csv': {
      const files = toCSV(result, schema);
      if (values.out) {
        mkdirSync(values.out, { recursive: true });
        for (const [table, text] of Object.entries(files)) writeFileSync(join(values.out, `${table}.csv`), text);
        process.stderr.write(`Wrote ${Object.keys(files).length} CSV file(s) to ${values.out}\n`);
      } else {
        for (const [table, text] of Object.entries(files)) process.stdout.write(`# ${table}.csv\n${text}\n`);
      }
      break;
    }
    default:
      throw new Error(`Unknown format "${values.format}" (use json, csv or sql)`);
  }
}

function emit(text, out) {
  if (out) {
    writeFileSync(out, text);
    process.stderr.write(`Wrote ${out}\n`);
  } else {
    process.stdout.write(text);
  }
}

// Only run when executed directly, so tests can import parseCounts.
const isMain = process.argv[1] && realpathSync(resolve(process.argv[1])) === realpathSync(fileURLToPath(import.meta.url));
if (isMain) {
  try {
    main(process.argv.slice(2));
  } catch (err) {
    process.stderr.write(`error: ${err.message}\n`);
    process.exitCode = 1;
  }
}
