import type { Units } from './types';

/** Formatting helpers. Pure functions so they are trivial to unit test. */

export function temperatureUnit(units: Units): string {
  return units === 'metric' ? '°C' : '°F';
}

export function speedUnit(units: Units): string {
  return units === 'metric' ? 'km/h' : 'mph';
}

/** Rounds to the nearest degree; avoids printing "-0°". */
export function formatTemperature(value: number, units: Units, withUnit = false): string {
  const rounded = Math.round(value);
  const safe = Object.is(rounded, -0) ? 0 : rounded;
  return withUnit ? `${safe}${temperatureUnit(units)}` : `${safe}°`;
}

export function formatSpeed(value: number, units: Units): string {
  return `${Math.round(value)} ${speedUnit(units)}`;
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

/**
 * Formats a YYYY-MM-DD date as a weekday. The API already returns dates in
 * the location's timezone, so we parse the components directly instead of
 * going through `new Date(string)` (which would apply the *device's* zone).
 */
export function formatWeekday(isoDate: string, todayIso?: string): string {
  if (todayIso && isoDate === todayIso) return 'Today';
  const [y, m, d] = isoDate.split('-').map(Number);
  const day = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return WEEKDAYS[day];
}

/** "2026-11-06T14:00" -> "2 PM" (local time of the forecast location). */
export function formatHour(isoLocal: string): string {
  const match = /T(\d{2})/.exec(isoLocal);
  if (!match) return isoLocal;
  const hour = Number(match[1]);
  const suffix = hour < 12 ? 'AM' : 'PM';
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${h12} ${suffix}`;
}
