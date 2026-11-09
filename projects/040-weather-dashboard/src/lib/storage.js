import { UNITS, isUnit } from './units.js';

const UNIT_KEY = 'weather-dashboard:unit';
const CITY_KEY = 'weather-dashboard:city';

// Storage can throw (private browsing, blocked site data), and its contents
// may be stale or hand-edited. Neither may stop the app from starting.
function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Preferences are a convenience; the app works without them.
  }
}

export function loadUnit() {
  const stored = read(UNIT_KEY);
  return isUnit(stored) ? stored : UNITS.METRIC;
}

export const saveUnit = (unit) => write(UNIT_KEY, unit);

export function loadCity() {
  try {
    const city = JSON.parse(read(CITY_KEY));
    const valid =
      typeof city?.name === 'string' &&
      Number.isFinite(city.latitude) &&
      Number.isFinite(city.longitude);
    return valid ? city : null;
  } catch {
    return null;
  }
}

export const saveCity = (city) => write(CITY_KEY, JSON.stringify(city));
