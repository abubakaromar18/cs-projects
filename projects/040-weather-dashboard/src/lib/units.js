/** Display units. Stored values are always Celsius and km/h. */
export const UNITS = Object.freeze({ METRIC: 'metric', IMPERIAL: 'imperial' });

export const celsiusToFahrenheit = (c) => (c * 9) / 5 + 32;
export const kmhToMph = (kmh) => kmh / 1.609344;

export const isUnit = (value) => Object.values(UNITS).includes(value);

const MISSING = '–';
const isNumber = (value) => typeof value === 'number' && Number.isFinite(value);

/** Format a Celsius reading, e.g. "21°" or, with showUnit, "21°C". */
export function formatTemperature(celsius, unit, { showUnit = false } = {}) {
  if (!isNumber(celsius)) return MISSING;
  const metric = unit === UNITS.METRIC;
  const value = Math.round(metric ? celsius : celsiusToFahrenheit(celsius));
  // Adding 0 turns the -0 from rounding (e.g. -0.4) into plain 0.
  return `${value + 0}°${showUnit ? (metric ? 'C' : 'F') : ''}`;
}

export function formatWindSpeed(kmh, unit) {
  if (!isNumber(kmh)) return MISSING;
  return unit === UNITS.METRIC ? `${Math.round(kmh)} km/h` : `${Math.round(kmhToMph(kmh))} mph`;
}

export function formatPercent(value) {
  return isNumber(value) ? `${Math.round(value)}%` : MISSING;
}
