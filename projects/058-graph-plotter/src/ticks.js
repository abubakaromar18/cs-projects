/**
 * "Nice" axis ticks.
 *
 * Given a visible range and a desired number of ticks, choose a step of the
 * form {1, 2, 5} × 10^n — the classic Heckbert "nice numbers" approach — so
 * labels read 0, 0.5, 1, 1.5 rather than 0, 0.37, 0.74.
 */

export function niceStep(span, targetTicks = 8) {
  if (!(span > 0) || !Number.isFinite(span)) throw new RangeError('span must be a positive finite number');
  const raw = span / targetTicks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag; // in [1, 10)
  let nice;
  if (norm < 1.5) nice = 1;
  else if (norm < 3.5) nice = 2;
  else if (norm < 7.5) nice = 5;
  else nice = 10;
  return nice * mag;
}

/** All multiples of `step` within [min, max]. */
export function ticks(min, max, targetTicks = 8) {
  const step = niceStep(max - min, targetTicks);
  const first = Math.ceil(min / step);
  const last = Math.floor(max / step);
  const out = [];
  for (let i = first; i <= last; i++) {
    // Multiply the integer index (rather than accumulating) to avoid drift,
    // then snap tiny values to exactly 0.
    const v = i * step;
    out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  }
  return { step, values: out };
}

/**
 * Format a tick label with just enough decimals for the given step, switching
 * to exponent notation for very large/small magnitudes.
 */
export function formatTick(value, step) {
  if (value === 0) return '0';
  const abs = Math.abs(value);
  if (abs >= 1e6 || abs < 1e-4) {
    const digits = Math.max(0, Math.ceil(-Math.log10(step / abs)) - 1);
    return value.toExponential(Math.min(digits, 6)).replace(/\.?0+e/, 'e');
  }
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  return value.toFixed(decimals);
}
