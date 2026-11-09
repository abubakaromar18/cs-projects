import { beforeEach, describe, expect, it, vi } from 'vitest';
import { formatDay } from '../src/lib/dates.js';
import { loadCity, loadUnit, saveCity, saveUnit } from '../src/lib/storage.js';
import { barGeometry, overallRange } from '../src/lib/tempRange.js';
import {
  UNITS,
  celsiusToFahrenheit,
  formatPercent,
  formatTemperature,
  formatWindSpeed,
  kmhToMph,
} from '../src/lib/units.js';
import { describeWeather } from '../src/lib/weatherCodes.js';
import { BERLIN } from './fixtures.js';

const { METRIC, IMPERIAL } = UNITS;

describe('units', () => {
  it('converts at known points', () => {
    expect(celsiusToFahrenheit(0)).toBe(32);
    expect(celsiusToFahrenheit(100)).toBe(212);
    expect(celsiusToFahrenheit(-40)).toBe(-40);
    expect(kmhToMph(1.609344)).toBeCloseTo(1);
  });

  it('formats temperatures in either unit', () => {
    expect(formatTemperature(21.6, METRIC)).toBe('22°');
    expect(formatTemperature(20, IMPERIAL, { showUnit: true })).toBe('68°F');
    expect(formatTemperature(20, METRIC, { showUnit: true })).toBe('20°C');
  });

  it('never prints negative zero', () => {
    expect(formatTemperature(-0.4, METRIC)).toBe('0°');
  });

  it('shows zero but marks missing readings', () => {
    expect(formatTemperature(0, METRIC)).toBe('0°');
    expect(formatTemperature(null, METRIC)).toBe('–');
    expect(formatWindSpeed(null, METRIC)).toBe('–');
    expect(formatPercent(null)).toBe('–');
    expect(formatPercent(0)).toBe('0%');
  });

  it('formats wind speed', () => {
    expect(formatWindSpeed(16.4, METRIC)).toBe('16 km/h');
    expect(formatWindSpeed(16.09344, IMPERIAL)).toBe('10 mph');
  });
});

describe('describeWeather', () => {
  it('labels known codes', () => {
    expect(describeWeather(61).label).toBe('Light rain');
  });

  it('falls back on unknown or missing codes', () => {
    expect(describeWeather(1234).label).toBe('Unknown');
    expect(describeWeather(null).label).toBe('Unknown');
  });

  it('uses a moon only for clear nights', () => {
    expect(describeWeather(0, { isDay: false }).icon).toBe('🌙');
    expect(describeWeather(61, { isDay: false }).icon).not.toBe('🌙');
    expect(describeWeather(0).icon).not.toBe('🌙');
  });
});

describe('formatDay', () => {
  it('does not shift the date, whatever the browser time zone', () => {
    // 2026-11-09 is a Monday. Parsed naively it would be Sunday in the Americas.
    expect(formatDay('2026-11-09')).toEqual({ weekday: 'Mon', date: 'Nov 9' });
  });

  it('labels today', () => {
    expect(formatDay('2026-11-09', { today: true }).weekday).toBe('Today');
  });
});

describe('temperature bars', () => {
  const days = [
    { low: 0, high: 10 },
    { low: 5, high: 20 },
  ];

  it('finds the overall range', () => {
    expect(overallRange(days)).toEqual({ min: 0, max: 20 });
    expect(overallRange([{ low: null, high: null }])).toBeNull();
  });

  it('places bars on the shared scale', () => {
    const range = overallRange(days);
    expect(barGeometry(days[0], range)).toEqual({ left: 0, width: 50 });
    expect(barGeometry(days[1], range)).toEqual({ left: 25, width: 75 });
  });

  it('avoids dividing by zero and skips missing data', () => {
    expect(barGeometry({ low: 5, high: 5 }, { min: 5, max: 5 })).toEqual({ left: 0, width: 100 });
    expect(barGeometry({ low: null, high: 5 }, { min: 0, max: 5 })).toBeNull();
  });
});

describe('storage', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips preferences', () => {
    saveUnit(IMPERIAL);
    saveCity(BERLIN);
    expect(loadUnit()).toBe(IMPERIAL);
    expect(loadCity()).toEqual(BERLIN);
  });

  it('uses defaults when empty', () => {
    expect(loadUnit()).toBe(METRIC);
    expect(loadCity()).toBeNull();
  });

  it('ignores corrupt values', () => {
    localStorage.setItem('weather-dashboard:unit', 'kelvin');
    localStorage.setItem('weather-dashboard:city', '{not json');
    expect(loadUnit()).toBe(METRIC);
    expect(loadCity()).toBeNull();
    localStorage.setItem('weather-dashboard:city', '{"name":"X","latitude":"north"}');
    expect(loadCity()).toBeNull();
  });

  it('survives storage that throws', () => {
    const denied = () => {
      throw new DOMException('denied', 'SecurityError');
    };
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(denied);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(denied);
    expect(loadUnit()).toBe(METRIC);
    expect(loadCity()).toBeNull();
    expect(() => saveUnit(IMPERIAL)).not.toThrow();
  });
});
