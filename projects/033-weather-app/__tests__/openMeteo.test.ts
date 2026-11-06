import {
  buildForecastUrl,
  buildGeocodingUrl,
  firstUpcomingHourIndex,
  HOURS_AHEAD,
  parseForecast,
  parseGeocoding,
  WeatherApiError,
  WeatherClient,
} from '../src/api/openMeteo';
import { makeRawForecast, okResponse } from '../testing/fixtures';

const chicago = { latitude: 41.8781, longitude: -87.6298 };

describe('URL builders', () => {
  it('builds a metric forecast URL with rounded coordinates', () => {
    const url = new URL(buildForecastUrl(chicago, 'metric'));
    expect(url.searchParams.get('latitude')).toBe('41.88');
    expect(url.searchParams.get('longitude')).toBe('-87.63');
    expect(url.searchParams.get('timezone')).toBe('auto');
    expect(url.searchParams.get('temperature_unit')).toBeNull();
  });

  it('adds imperial unit params', () => {
    const url = new URL(buildForecastUrl(chicago, 'imperial'));
    expect(url.searchParams.get('temperature_unit')).toBe('fahrenheit');
    expect(url.searchParams.get('wind_speed_unit')).toBe('mph');
  });

  it('encodes geocoding queries', () => {
    const url = new URL(buildGeocodingUrl('  São Paulo '));
    expect(url.searchParams.get('name')).toBe('São Paulo');
  });
});

describe('parseForecast', () => {
  it('maps the raw response into domain types', () => {
    const f = parseForecast(makeRawForecast(), 'metric');
    expect(f.timezone).toBe('America/Chicago');
    expect(f.current).toMatchObject({ temperature: 11.6, humidity: 62, isDay: true, weatherCode: 2 });
    expect(f.daily).toHaveLength(7);
    expect(f.daily[2]).toEqual({ date: '2026-11-08', high: 8, low: -1, precipitationProbability: 10, weatherCode: 3 });
  });

  it('starts the hourly strip at the current hour and takes 24 points', () => {
    const f = parseForecast(makeRawForecast(), 'metric');
    expect(f.hourly).toHaveLength(HOURS_AHEAD);
    expect(f.hourly[0].time).toBe('2026-11-06T14:00');
    expect(f.hourly[23].time).toBe('2026-11-07T13:00');
  });

  it('rejects malformed responses', () => {
    expect(() => parseForecast({}, 'metric')).toThrow(WeatherApiError);
    const raw = makeRawForecast() as any;
    delete raw.daily.time;
    expect(() => parseForecast(raw, 'metric')).toThrow(/daily|time/);
  });

  it('finds the upcoming hour index', () => {
    const times = ['2026-11-06T13:00', '2026-11-06T14:00', '2026-11-06T15:00'];
    expect(firstUpcomingHourIndex(times, '2026-11-06T14:45')).toBe(1);
    expect(firstUpcomingHourIndex(times, '2026-11-07T00:00')).toBe(0);
  });
});

describe('parseGeocoding', () => {
  it('builds display names and handles empty results', () => {
    expect(
      parseGeocoding({ results: [{ name: 'Chicago', admin1: 'Illinois', country_code: 'US', latitude: 41.85, longitude: -87.65 }] }),
    ).toEqual([{ name: 'Chicago, Illinois, US', latitude: 41.85, longitude: -87.65 }]);
    expect(parseGeocoding({ generationtime_ms: 0.4 })).toEqual([]);
  });
});

describe('WeatherClient', () => {
  it('caches forecasts per URL until the TTL expires', async () => {
    let now = 0;
    const fetch = jest.fn(() => okResponse(makeRawForecast()));
    const client = new WeatherClient({ fetch, cacheTtlMs: 1000, now: () => now });

    await client.getForecast(chicago, 'metric');
    await client.getForecast({ latitude: 41.8799, longitude: -87.6301 }, 'metric'); // same rounded cell
    expect(fetch).toHaveBeenCalledTimes(1);

    await client.getForecast(chicago, 'imperial'); // different units -> different key
    expect(fetch).toHaveBeenCalledTimes(2);

    now = 1001;
    await client.getForecast(chicago, 'metric');
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it('bypasses the cache when forced', async () => {
    const fetch = jest.fn(() => okResponse(makeRawForecast()));
    const client = new WeatherClient({ fetch });
    await client.getForecast(chicago, 'metric');
    await client.getForecast(chicago, 'metric', { force: true });
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('surfaces HTTP and network errors as WeatherApiError', async () => {
    const httpFail = new WeatherClient({ fetch: () => Promise.resolve({ ok: false, status: 503, json: async () => ({}) }) });
    await expect(httpFail.getForecast(chicago, 'metric')).rejects.toMatchObject({ name: 'WeatherApiError', status: 503 });

    const netFail = new WeatherClient({ fetch: () => Promise.reject(new TypeError('Network request failed')) });
    await expect(netFail.getForecast(chicago, 'metric')).rejects.toThrow(/Network error/);
  });

  it('skips geocoding for very short queries', async () => {
    const fetch = jest.fn();
    const client = new WeatherClient({ fetch });
    expect(await client.searchPlaces('a')).toEqual([]);
    expect(fetch).not.toHaveBeenCalled();
  });
});
