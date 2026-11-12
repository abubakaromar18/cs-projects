/**
 * Field generators.
 *
 * Each generator is a pure function `(rng, options, ctx) => value`.
 *   - rng     : a seeded Random instance (never Math.random)
 *   - options : the field's spec from the schema (min, max, values, ...)
 *   - ctx     : { row, index, table } — the partially built row, its 0-based
 *               index, and the table name. Lets generators derive values from
 *               earlier fields (e.g. an email built from first/last name).
 *
 * This is a classic *strategy registry*: the seeder looks up a strategy by
 * name, so adding a new type is one entry in GENERATORS.
 */
import * as W from './words.js';

const pad = (n, width = 2) => String(n).padStart(width, '0');

function slugify(s) {
  return String(s)
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '');
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function words(rng, n) {
  return Array.from({ length: n }, () => rng.pick(W.LOREM));
}

/** Parse a date option: accepts ISO strings or 'now'. */
function toDate(v, fallback) {
  if (v === undefined) return fallback;
  if (v === 'now') return new Date();
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) throw new Error(`Invalid date: ${v}`);
  return d;
}

export const GENERATORS = {
  // ---- identifiers --------------------------------------------------------
  /** Auto-incrementing integer, 1-based by default. */
  serial: (_rng, opts, ctx) => (opts.start ?? 1) + ctx.index,

  /** RFC 4122 version-4 UUID built from the seeded RNG (reproducible). */
  uuid: (rng) => {
    const bytes = Array.from({ length: 16 }, () => rng.int(0, 255));
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10xx
    const hex = bytes.map((b) => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  },

  // ---- primitives ---------------------------------------------------------
  int: (rng, opts) => rng.int(opts.min ?? 0, opts.max ?? 1000),
  float: (rng, opts) => rng.float(opts.min ?? 0, opts.max ?? 1, opts.decimals ?? 2),
  boolean: (rng, opts) => rng.chance(opts.probability ?? 0.5),

  /** Pick from a fixed list, optionally weighted. */
  enum: (rng, opts) => {
    if (!Array.isArray(opts.values) || opts.values.length === 0) {
      throw new Error('enum field requires a non-empty "values" array');
    }
    return opts.weights ? rng.weighted(opts.values, opts.weights) : rng.pick(opts.values);
  },

  /** A constant value — handy for defaults or for overriding during tests. */
  constant: (_rng, opts) => opts.value,

  /**
   * Template string with {{field}} placeholders referencing earlier fields,
   * plus {{index}}. Example: "{{first_name}} {{last_name}}".
   */
  template: (_rng, opts, ctx) =>
    String(opts.pattern ?? '').replace(/\{\{\s*(\w+)\s*\}\}/g, (_, key) => {
      if (key === 'index') return String(ctx.index);
      const v = ctx.row[key];
      if (v === undefined) throw new Error(`template references unknown or later field "${key}"`);
      return String(v);
    }),

  // ---- people -------------------------------------------------------------
  firstName: (rng) => rng.pick(W.FIRST_NAMES),
  lastName: (rng) => rng.pick(W.LAST_NAMES),
  fullName: (rng) => `${rng.pick(W.FIRST_NAMES)} ${rng.pick(W.LAST_NAMES)}`,

  /**
   * Email. If the row already has first/last name fields (configurable via
   * opts.from), reuse them so the data looks internally consistent.
   */
  email: (rng, opts, ctx) => {
    const [fKey, lKey] = opts.from ?? ['first_name', 'last_name'];
    const first = ctx.row[fKey] ?? rng.pick(W.FIRST_NAMES);
    const last = ctx.row[lKey] ?? rng.pick(W.LAST_NAMES);
    const suffix = rng.chance(0.5) ? String(rng.int(1, 999)) : '';
    const domain = opts.domain ?? rng.pick(W.EMAIL_DOMAINS);
    return `${slugify(first)}.${slugify(last)}${suffix}@${domain}`;
  },

  username: (rng, _opts, ctx) => {
    const base = ctx.row.first_name ?? rng.pick(W.FIRST_NAMES);
    return `${slugify(base).replace(/\./g, '_')}${rng.int(10, 9999)}`;
  },

  /** Reserved 555-01xx range: never a real number. */
  phone: (rng) => `+1-${rng.int(200, 999)}-555-01${pad(rng.int(0, 99))}`,

  // ---- places -------------------------------------------------------------
  street: (rng) => `${rng.int(1, 9999)} ${rng.pick(W.STREET_NAMES)} ${rng.pick(W.STREET_SUFFIXES)}`,
  city: (rng) => rng.pick(W.CITIES),
  country: (rng) => rng.pick(W.COUNTRIES),
  zip: (rng) => pad(rng.int(0, 99999), 5),

  // ---- business -----------------------------------------------------------
  company: (rng) => `${rng.pick(W.COMPANY_PREFIXES)} ${rng.pick(W.COMPANY_NOUNS)}`,
  productName: (rng) =>
    `${rng.pick(W.PRODUCT_ADJECTIVES)} ${rng.pick(W.PRODUCT_MATERIALS)} ${rng.pick(W.PRODUCT_NOUNS)}`,
  price: (rng, opts) => rng.float(opts.min ?? 1, opts.max ?? 500, 2),

  // ---- text ---------------------------------------------------------------
  word: (rng) => rng.pick(W.LOREM),
  sentence: (rng, opts) => {
    const n = rng.int(opts.minWords ?? 4, opts.maxWords ?? 12);
    return capitalize(words(rng, n).join(' ')) + '.';
  },
  paragraph: (rng, opts) => {
    const n = rng.int(opts.minSentences ?? 2, opts.maxSentences ?? 5);
    return Array.from({ length: n }, () => GENERATORS.sentence(rng, {})).join(' ');
  },
  /** Title-cased short phrase, e.g. for post titles. */
  title: (rng, opts) => {
    const n = rng.int(opts.minWords ?? 2, opts.maxWords ?? 6);
    return words(rng, n).map(capitalize).join(' ');
  },
  slug: (rng, opts, ctx) => {
    const src = opts.from ? ctx.row[opts.from] : words(rng, 3).join(' ');
    return slugify(src).replace(/\./g, '-');
  },

  // ---- time ---------------------------------------------------------------
  /**
   * Timestamp between `from` and `to` (ISO strings or 'now').
   * `after` names an earlier field in the same row: the value will be >= it,
   * which keeps e.g. updated_at >= created_at.
   */
  datetime: (rng, opts, ctx) => {
    let from = toDate(opts.from, new Date('2020-01-01T00:00:00Z'));
    const to = toDate(opts.to, new Date('2026-01-01T00:00:00Z'));
    if (opts.after && ctx.row[opts.after]) {
      const prev = new Date(ctx.row[opts.after]);
      if (prev > from) from = prev;
    }
    const t = from.getTime() + Math.floor(rng.next() * Math.max(0, to.getTime() - from.getTime()));
    return new Date(t).toISOString();
  },
  date: (rng, opts, ctx) => GENERATORS.datetime(rng, opts, ctx).slice(0, 10),

  // ---- web ----------------------------------------------------------------
  url: (rng) => `https://${rng.pick(W.EMAIL_DOMAINS)}/${words(rng, 2).join('-')}`,
  ipv4: (rng) => `10.${rng.int(0, 255)}.${rng.int(0, 255)}.${rng.int(1, 254)}`, // private range only
  hexColor: (rng) => '#' + rng.int(0, 0xffffff).toString(16).padStart(6, '0'),
};

export function hasGenerator(type) {
  return Object.prototype.hasOwnProperty.call(GENERATORS, type);
}
