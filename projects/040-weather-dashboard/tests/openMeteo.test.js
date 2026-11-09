import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  buildForecastUrl,
  buildSearchUrl,
  fetchForecast,
  parseCities,
  parseForecast,
  searchCities,
} from '../src/api/openMeteo.js';
import { BERLIN, forecastBody, geocodingBody, jsonResponse } from './fixtures.js';

afterEach(() => vi.unstubAllGlobals());

describe('URLs', () => {
  it('encodes the search term', () => {
    const url = new URL(buildSearchUrl('São Paulo & co'));
    expect(url.hostname).toBe('geocoding-api.open-meteo.com');
    expect(url.searchParams.get('name')).toBe('São Paulo & co');
  });

  it('requests five days in the city time zone', () => {
    const { searchParams } = new URL(buildForecastUrl(BERLIN));
    expect(searchParams.get('latitude')).toBe('52.52');
    expect(searchParams.get('forecast_days')).toBe('5');
    expect(searchParams.get('timezone')).toBe('auto');
  });
});

describe('parseCities', () => {
  it('maps API fields', () => {
    expect(parseCities(geocodingBody)[0]).toEqual(BERLIN);
  });

  it('treats a missing results field as no matches', () => {
    expect(parseCities({ generationtime_ms: 0.5 })).toEqual([]);
  });

  it('drops entries without coordinates', () => {
    expect(parseCities({ results: [{ id: 1, name: 'Nowhere' }] })).toEqual([]);
  });

  it('tolerates missing optional fields', () => {
    const [city] = parseCities({ results: [{ name: 'X', latitude: 0, longitude: 0 }] });
    expect(city).toMatchObject({ id: '0,0', region: '', country: '' });
  });
});

describe('parseForecast', () => {
  it('zips parallel daily arrays into day objects', () => {
    const { days } = parseForecast(forecastBody);
    expect(days).toHaveLength(5);
    expect(days[1]).toEqual({ date: '2026-11-10', code: 61, high: 15, low: 8, rainChance: 80 });
  });

  it('keeps null readings as null and zero as zero', () => {
    const { days } = parseForecast(forecastBody);
    expect(days[2].rainChance).toBeNull();
    expect(days[3].rainChance).toBe(0);
    expect(days[2].low).toBe(0);
  });

  it('reads is_day as a flag', () => {
    const night = { ...forecastBody, current: { ...forecastBody.current, is_day: 0 } };
    expect(parseForecast(night).current.isDay).toBe(false);
    expect(parseForecast(forecastBody).current.isDay).toBe(true);
  });

  it('rejects incomplete data', () => {
    expect(() => parseForecast({ current: {} })).toThrow(ApiError);
    expect(() => parseForecast(null)).toThrow(ApiError);
  });
});

describe('requests', () => {
  it('returns parsed cities', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(geocodingBody)));
    await expect(searchCities('Berlin')).resolves.toHaveLength(2);
  });

  it('surfaces the API reason on HTTP errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ error: true, reason: 'Latitude out of range' }, 400)),
    );
    const error = await fetchForecast(BERLIN).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(400);
    expect(error.message).toContain('Latitude out of range');
  });

  it('reports a non-JSON error page as an HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<h1>Bad gateway</h1>', { status: 502 })));
    await expect(fetchForecast(BERLIN)).rejects.toMatchObject({ name: 'ApiError', status: 502 });
  });

  it('reports malformed success bodies', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('oops')));
    await expect(fetchForecast(BERLIN)).rejects.toThrow(/unreadable/);
  });

  it('wraps network failures in a friendly message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))));
    await expect(fetchForecast(BERLIN)).rejects.toThrow(/Check your connection/);
  });

  // A fetch that never answers, and rejects only when its signal aborts.
  const hangingFetch = (_url, { signal }) =>
    new Promise((_, reject) => {
      signal.addEventListener('abort', () => reject(signal.reason));
    });

  it('times out slow requests', async () => {
    vi.stubGlobal('fetch', vi.fn(hangingFetch));
    await expect(fetchForecast(BERLIN, { timeoutMs: 5 })).rejects.toThrow(/too long/);
  });

  it('passes caller aborts through unwrapped', async () => {
    vi.stubGlobal('fetch', vi.fn(hangingFetch));
    const controller = new AbortController();
    const pending = fetchForecast(BERLIN, { signal: controller.signal });
    controller.abort();
    const error = await pending.catch((e) => e);
    expect(error).not.toBeInstanceOf(ApiError);
    expect(error.name).toBe('AbortError');
  });
});
