/**
 * Client for the Open-Meteo forecast and geocoding APIs.
 * Open-Meteo is free for non-commercial use and needs no API key.
 *
 * Design notes:
 *  - `fetch` is injected so the client can be tested without the network.
 *  - Raw JSON is validated and mapped into our own domain types, so the rest
 *    of the app never depends on the wire format.
 */
import { TTLCache } from './cache';
import type { Coordinates, DailyPoint, Forecast, HourlyPoint, Place, Units } from '../domain/types';

export const FORECAST_URL = 'https://api.open-meteo.com/v1/forecast';
export const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search';

export type FetchLike = (url: string, init?: { signal?: AbortSignal }) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}>;

export class WeatherApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = 'WeatherApiError';
  }
}

/** Number of hourly points shown in the hourly strip. */
export const HOURS_AHEAD = 24;

/** Rounds coordinates so nearby requests share cache entries (~1 km). */
function roundCoord(n: number): number {
  return Math.round(n * 100) / 100;
}

export function buildForecastUrl({ latitude, longitude }: Coordinates, units: Units): string {
  const params = new URLSearchParams({
    latitude: String(roundCoord(latitude)),
    longitude: String(roundCoord(longitude)),
    current: 'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day',
    hourly: 'temperature_2m,precipitation_probability,weather_code',
    daily: 'temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code',
    timezone: 'auto',
    forecast_days: '7',
  });
  if (units === 'imperial') {
    params.set('temperature_unit', 'fahrenheit');
    params.set('wind_speed_unit', 'mph');
  }
  return `${FORECAST_URL}?${params.toString()}`;
}

export function buildGeocodingUrl(query: string, count = 5): string {
  const params = new URLSearchParams({ name: query.trim(), count: String(count), language: 'en', format: 'json' });
  return `${GEOCODING_URL}?${params.toString()}`;
}

// ---------- response parsing ----------

type Json = Record<string, any>;

function requireArray(obj: Json | undefined, key: string): any[] {
  const v = obj?.[key];
  if (!Array.isArray(v)) throw new WeatherApiError(`Malformed response: missing "${key}"`);
  return v;
}

/** Index of the first hourly slot at or after the current hour. */
export function firstUpcomingHourIndex(times: string[], currentTime: string): number {
  const currentHour = currentTime.slice(0, 13); // "YYYY-MM-DDTHH"
  // ISO strings in the same zone sort lexicographically == chronologically.
  const idx = times.findIndex((t) => t.slice(0, 13) >= currentHour);
  return idx === -1 ? 0 : idx;
}

export function parseForecast(raw: unknown, units: Units): Forecast {
  const json = raw as Json;
  const c = json?.current;
  if (!c || typeof c.temperature_2m !== 'number') {
    throw new WeatherApiError('Malformed response: missing current conditions');
  }

  const hTimes = requireArray(json.hourly, 'time') as string[];
  const hTemp = requireArray(json.hourly, 'temperature_2m');
  const hPrecip = requireArray(json.hourly, 'precipitation_probability');
  const hCode = requireArray(json.hourly, 'weather_code');

  const start = firstUpcomingHourIndex(hTimes, c.time);
  const hourly: HourlyPoint[] = hTimes.slice(start, start + HOURS_AHEAD).map((time, i) => ({
    time,
    temperature: hTemp[start + i],
    precipitationProbability: hPrecip[start + i] ?? 0,
    weatherCode: hCode[start + i],
  }));

  const dTimes = requireArray(json.daily, 'time') as string[];
  const dMax = requireArray(json.daily, 'temperature_2m_max');
  const dMin = requireArray(json.daily, 'temperature_2m_min');
  const dPrecip = requireArray(json.daily, 'precipitation_probability_max');
  const dCode = requireArray(json.daily, 'weather_code');

  const daily: DailyPoint[] = dTimes.map((date, i) => ({
    date,
    high: dMax[i],
    low: dMin[i],
    precipitationProbability: dPrecip[i] ?? 0,
    weatherCode: dCode[i],
  }));

  return {
    timezone: json.timezone ?? 'UTC',
    units,
    current: {
      time: c.time,
      temperature: c.temperature_2m,
      apparentTemperature: c.apparent_temperature,
      humidity: c.relative_humidity_2m,
      windSpeed: c.wind_speed_10m,
      weatherCode: c.weather_code,
      isDay: c.is_day === 1,
    },
    hourly,
    daily,
  };
}

export function parseGeocoding(raw: unknown): Place[] {
  const results = (raw as Json)?.results;
  if (!Array.isArray(results)) return []; // API omits "results" when nothing matches
  return results.map((r: Json) => ({
    latitude: r.latitude,
    longitude: r.longitude,
    name: [r.name, r.admin1, r.country_code].filter(Boolean).join(', '),
  }));
}

// ---------- client ----------

export interface WeatherClientOptions {
  fetch?: FetchLike;
  cacheTtlMs?: number;
  now?: () => number;
}

export class WeatherClient {
  private readonly fetchFn: FetchLike;
  private readonly cache: TTLCache<Forecast>;

  constructor(opts: WeatherClientOptions = {}) {
    this.fetchFn = opts.fetch ?? (globalThis.fetch as unknown as FetchLike);
    this.cache = new TTLCache<Forecast>(opts.cacheTtlMs ?? 10 * 60 * 1000, 20, opts.now);
  }

  private async getJson(url: string, signal?: AbortSignal): Promise<unknown> {
    let res;
    try {
      res = await this.fetchFn(url, { signal });
    } catch (e) {
      if ((e as Error)?.name === 'AbortError') throw e;
      throw new WeatherApiError('Network error — check your connection.');
    }
    if (!res.ok) throw new WeatherApiError(`Weather service returned HTTP ${res.status}`, res.status);
    return res.json();
  }

  async getForecast(coords: Coordinates, units: Units, opts: { signal?: AbortSignal; force?: boolean } = {}): Promise<Forecast> {
    const url = buildForecastUrl(coords, units);
    if (!opts.force) {
      const hit = this.cache.get(url);
      if (hit) return hit;
    }
    const forecast = parseForecast(await this.getJson(url, opts.signal), units);
    this.cache.set(url, forecast);
    return forecast;
  }

  async searchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
    if (query.trim().length < 2) return [];
    return parseGeocoding(await this.getJson(buildGeocodingUrl(query), signal));
  }
}

/** Shared default instance used by the app. */
export const weatherClient = new WeatherClient();
