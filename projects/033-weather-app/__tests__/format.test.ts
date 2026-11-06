import { formatHour, formatSpeed, formatTemperature, formatWeekday, temperatureUnit } from '../src/domain/format';
import { describeWeather, weatherIcon } from '../src/domain/weatherCodes';

describe('format', () => {
  it('rounds temperatures and never prints -0', () => {
    expect(formatTemperature(11.6, 'metric')).toBe('12°');
    expect(formatTemperature(-0.3, 'metric')).toBe('0°');
    expect(formatTemperature(-2.6, 'metric')).toBe('-3°');
    expect(formatTemperature(70.4, 'imperial', true)).toBe('70°F');
    expect(temperatureUnit('metric')).toBe('°C');
  });

  it('formats speeds with the right unit', () => {
    expect(formatSpeed(18.4, 'metric')).toBe('18 km/h');
    expect(formatSpeed(11.5, 'imperial')).toBe('12 mph');
  });

  it('formats weekdays independent of device timezone', () => {
    expect(formatWeekday('2026-11-06')).toBe('Fri');
    expect(formatWeekday('2026-11-08')).toBe('Sun');
    expect(formatWeekday('2026-11-06', '2026-11-06')).toBe('Today');
  });

  it('formats hours in 12-hour clock', () => {
    expect(formatHour('2026-11-06T00:00')).toBe('12 AM');
    expect(formatHour('2026-11-06T09:00')).toBe('9 AM');
    expect(formatHour('2026-11-06T12:00')).toBe('12 PM');
    expect(formatHour('2026-11-06T23:00')).toBe('11 PM');
    expect(formatHour('garbage')).toBe('garbage');
  });
});

describe('weatherCodes', () => {
  it('maps known WMO codes', () => {
    expect(describeWeather(0).label).toBe('Clear sky');
    expect(describeWeather(95).label).toBe('Thunderstorm');
  });
  it('falls back for unknown codes', () => {
    expect(describeWeather(42).label).toBe('Unknown');
  });
  it('picks day/night icons', () => {
    expect(weatherIcon(0, true)).toBe('☀️');
    expect(weatherIcon(0, false)).toBe('🌙');
  });
});
