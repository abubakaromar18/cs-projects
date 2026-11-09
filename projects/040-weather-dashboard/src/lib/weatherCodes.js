/** WMO weather interpretation codes, as used by Open-Meteo. */
const CODES = new Map([
  [0, ['Clear sky', '☀️']],
  [1, ['Mainly clear', '🌤️']],
  [2, ['Partly cloudy', '⛅']],
  [3, ['Overcast', '☁️']],
  [45, ['Fog', '🌫️']],
  [48, ['Freezing fog', '🌫️']],
  [51, ['Light drizzle', '🌦️']],
  [53, ['Drizzle', '🌦️']],
  [55, ['Heavy drizzle', '🌧️']],
  [56, ['Light freezing drizzle', '🌧️']],
  [57, ['Freezing drizzle', '🌧️']],
  [61, ['Light rain', '🌦️']],
  [63, ['Rain', '🌧️']],
  [65, ['Heavy rain', '🌧️']],
  [66, ['Light freezing rain', '🌧️']],
  [67, ['Freezing rain', '🌧️']],
  [71, ['Light snow', '🌨️']],
  [73, ['Snow', '🌨️']],
  [75, ['Heavy snow', '❄️']],
  [77, ['Snow grains', '🌨️']],
  [80, ['Light showers', '🌦️']],
  [81, ['Showers', '🌧️']],
  [82, ['Violent showers', '⛈️']],
  [85, ['Light snow showers', '🌨️']],
  [86, ['Snow showers', '❄️']],
  [95, ['Thunderstorm', '⛈️']],
  [96, ['Thunderstorm with hail', '⛈️']],
  [99, ['Severe thunderstorm with hail', '⛈️']],
]);

/** Look up a label and icon. Clear codes get a moon at night. */
export function describeWeather(code, { isDay = true } = {}) {
  const [label, icon] = CODES.get(code) ?? ['Unknown', '❔'];
  return { label, icon: !isDay && (code === 0 || code === 1) ? '🌙' : icon };
}
