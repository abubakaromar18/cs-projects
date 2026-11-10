/**
 * Parsing of human-friendly expiry options ("10m", "1h", "1d", "never", ...).
 */

const UNIT_MS = {
  s: 1000,
  m: 60 * 1000,
  h: 60 * 60 * 1000,
  d: 24 * 60 * 60 * 1000,
  w: 7 * 24 * 60 * 60 * 1000,
};

/** Options offered in the web form, in display order. */
export const EXPIRY_CHOICES = [
  { value: '10m', label: '10 minutes' },
  { value: '1h', label: '1 hour' },
  { value: '1d', label: '1 day' },
  { value: '1w', label: '1 week' },
  { value: 'never', label: 'Never' },
];

export const MAX_TTL_MS = 30 * UNIT_MS.d;

/**
 * Convert an expiry string to milliseconds.
 * @returns {number|null} milliseconds, or null for "never"
 * @throws {RangeError} on malformed or out-of-range input
 */
export function parseExpiry(input) {
  if (input === undefined || input === null || input === '') return UNIT_MS.d; // default: 1 day
  const text = String(input).trim().toLowerCase();
  if (text === 'never') return null;

  const match = /^(\d+)\s*([smhdw])$/.exec(text);
  if (!match) {
    throw new RangeError(`Invalid expiry "${input}". Use e.g. 10m, 1h, 1d, 1w or never.`);
  }
  const ms = Number(match[1]) * UNIT_MS[match[2]];
  if (ms <= 0) throw new RangeError('Expiry must be positive.');
  if (ms > MAX_TTL_MS) throw new RangeError('Expiry cannot exceed 30 days.');
  return ms;
}

/** Render remaining lifetime as a short phrase, e.g. "in 3 hours". */
export function describeRemaining(expiresAt, now = Date.now()) {
  if (expiresAt === null) return 'never';
  const ms = Math.max(0, expiresAt - now);
  const units = [
    ['day', UNIT_MS.d],
    ['hour', UNIT_MS.h],
    ['minute', UNIT_MS.m],
    ['second', UNIT_MS.s],
  ];
  for (const [name, size] of units) {
    if (ms >= size) {
      const n = Math.floor(ms / size);
      return `in ${n} ${name}${n === 1 ? '' : 's'}`;
    }
  }
  return 'in less than a second';
}
