/**
 * WMO weather interpretation codes (WW), as used by Open-Meteo.
 * https://open-meteo.com/en/docs — "WMO Weather interpretation codes".
 *
 * A lookup table is the natural structure here: O(1) access and trivially
 * extensible. Codes not in the table fall back to "Unknown".
 */

export interface WeatherDescription {
  label: string;
  /** Emoji icons keep the app asset-free; [day, night]. */
  icon: [string, string];
}

const TABLE: Record<number, WeatherDescription> = {
  0: { label: 'Clear sky', icon: ['☀️', '🌙'] },
  1: { label: 'Mainly clear', icon: ['🌤️', '🌙'] },
  2: { label: 'Partly cloudy', icon: ['⛅', '☁️'] },
  3: { label: 'Overcast', icon: ['☁️', '☁️'] },
  45: { label: 'Fog', icon: ['🌫️', '🌫️'] },
  48: { label: 'Depositing rime fog', icon: ['🌫️', '🌫️'] },
  51: { label: 'Light drizzle', icon: ['🌦️', '🌧️'] },
  53: { label: 'Drizzle', icon: ['🌦️', '🌧️'] },
  55: { label: 'Dense drizzle', icon: ['🌧️', '🌧️'] },
  56: { label: 'Light freezing drizzle', icon: ['🌧️', '🌧️'] },
  57: { label: 'Freezing drizzle', icon: ['🌧️', '🌧️'] },
  61: { label: 'Light rain', icon: ['🌦️', '🌧️'] },
  63: { label: 'Rain', icon: ['🌧️', '🌧️'] },
  65: { label: 'Heavy rain', icon: ['🌧️', '🌧️'] },
  66: { label: 'Light freezing rain', icon: ['🌧️', '🌧️'] },
  67: { label: 'Freezing rain', icon: ['🌧️', '🌧️'] },
  71: { label: 'Light snow', icon: ['🌨️', '🌨️'] },
  73: { label: 'Snow', icon: ['🌨️', '🌨️'] },
  75: { label: 'Heavy snow', icon: ['❄️', '❄️'] },
  77: { label: 'Snow grains', icon: ['🌨️', '🌨️'] },
  80: { label: 'Light showers', icon: ['🌦️', '🌧️'] },
  81: { label: 'Showers', icon: ['🌧️', '🌧️'] },
  82: { label: 'Violent showers', icon: ['⛈️', '⛈️'] },
  85: { label: 'Light snow showers', icon: ['🌨️', '🌨️'] },
  86: { label: 'Snow showers', icon: ['❄️', '❄️'] },
  95: { label: 'Thunderstorm', icon: ['⛈️', '⛈️'] },
  96: { label: 'Thunderstorm with hail', icon: ['⛈️', '⛈️'] },
  99: { label: 'Severe thunderstorm with hail', icon: ['⛈️', '⛈️'] },
};

const UNKNOWN: WeatherDescription = { label: 'Unknown', icon: ['❔', '❔'] };

export function describeWeather(code: number): WeatherDescription {
  return TABLE[code] ?? UNKNOWN;
}

export function weatherIcon(code: number, isDay = true): string {
  const { icon } = describeWeather(code);
  return isDay ? icon[0] : icon[1];
}
