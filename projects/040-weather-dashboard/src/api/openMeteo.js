/**
 * Thin client for the Open-Meteo geocoding and forecast APIs (no key required).
 *
 * This module is the only code that knows the wire format. Everything else
 * works with the plain objects returned by `parseCities` and `parseForecast`.
 * Values are always requested in metric units; the unit toggle converts them
 * for display, so switching units needs no network request.
 */

const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search';
const FORECAST_URL = 'https://api.open-meteo.com/v1/forecast';
const DEFAULT_TIMEOUT_MS = 10_000;

export const FORECAST_DAYS = 5;

/** A failure worth showing to the user. Caller aborts are not wrapped. */
export class ApiError extends Error {
  constructor(message, { status } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function getJson(url, { signal, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const timeout = AbortSignal.timeout(timeoutMs);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;

  let response;
  try {
    response = await globalThis.fetch(url, { signal: combined });
  } catch (error) {
    // The caller cancelled on purpose, so let it recognise its own abort.
    if (signal?.aborted) throw error;
    if (timeout.aborted) throw new ApiError('The weather service took too long to respond.');
    throw new ApiError('Could not reach the weather service. Check your connection.');
  }

  let body = null;
  try {
    body = await response.json();
  } catch (error) {
    if (signal?.aborted) throw error;
    // Handled below: a non-JSON body is either an HTTP error or malformed.
  }

  if (!response.ok) {
    // Open-Meteo reports bad requests as { error: true, reason: "..." }.
    const reason = typeof body?.reason === 'string' ? `: ${body.reason}` : '';
    throw new ApiError(`The weather service returned an error${reason}`, {
      status: response.status,
    });
  }
  if (body === null || typeof body !== 'object') {
    throw new ApiError('The weather service sent an unreadable response.');
  }
  return body;
}

/** Convert a geocoding response to city objects, dropping unusable entries. */
export function parseCities(body) {
  // Open-Meteo omits `results` entirely when nothing matches.
  const results = Array.isArray(body?.results) ? body.results : [];
  return results
    .filter((r) => r.name && Number.isFinite(r.latitude) && Number.isFinite(r.longitude))
    .map((r) => ({
      id: r.id ?? `${r.latitude},${r.longitude}`,
      name: r.name,
      region: r.admin1 ?? '',
      country: r.country ?? '',
      latitude: r.latitude,
      longitude: r.longitude,
    }));
}

/**
 * Convert a forecast response to `{ timezone, current, days }`.
 * The API's `daily` block holds parallel arrays; `days` zips them into one
 * object per date. Individual readings may legitimately be null.
 */
export function parseForecast(body) {
  const { current, daily } = body ?? {};
  if (!current || !Array.isArray(daily?.time)) {
    throw new ApiError('The weather service sent an incomplete forecast.');
  }
  return {
    timezone: body.timezone ?? '',
    current: {
      temperature: current.temperature_2m ?? null,
      feelsLike: current.apparent_temperature ?? null,
      humidity: current.relative_humidity_2m ?? null,
      windSpeed: current.wind_speed_10m ?? null,
      code: current.weather_code ?? null,
      isDay: current.is_day !== 0,
    },
    days: daily.time.map((date, i) => ({
      date,
      code: daily.weather_code?.[i] ?? null,
      high: daily.temperature_2m_max?.[i] ?? null,
      low: daily.temperature_2m_min?.[i] ?? null,
      rainChance: daily.precipitation_probability_max?.[i] ?? null,
    })),
  };
}

export function buildSearchUrl(name) {
  const params = new URLSearchParams({ name, count: '6', language: 'en', format: 'json' });
  return `${GEOCODING_URL}?${params}`;
}

export function buildForecastUrl({ latitude, longitude }) {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    current:
      'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day',
    daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
    // "auto" makes each day start at midnight in the city, not in the browser.
    timezone: 'auto',
    forecast_days: String(FORECAST_DAYS),
  });
  return `${FORECAST_URL}?${params}`;
}

export async function searchCities(name, options) {
  return parseCities(await getJson(buildSearchUrl(name), options));
}

export async function fetchForecast(city, options) {
  return parseForecast(await getJson(buildForecastUrl(city), options));
}
