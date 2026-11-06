/** A trimmed but realistic Open-Meteo forecast response. */
export function makeRawForecast() {
  const hourlyTimes: string[] = [];
  for (let d = 6; d <= 7; d++) {
    for (let h = 0; h < 24; h++) hourlyTimes.push(`2026-11-0${d}T${String(h).padStart(2, '0')}:00`);
  }
  return {
    latitude: 41.88,
    longitude: -87.63,
    timezone: 'America/Chicago',
    current: {
      time: '2026-11-06T14:15',
      temperature_2m: 11.6,
      apparent_temperature: 9.2,
      relative_humidity_2m: 62,
      wind_speed_10m: 18.4,
      weather_code: 2,
      is_day: 1,
    },
    hourly: {
      time: hourlyTimes,
      temperature_2m: hourlyTimes.map((_, i) => 5 + (i % 24) / 2),
      precipitation_probability: hourlyTimes.map((_, i) => (i % 5) * 10),
      weather_code: hourlyTimes.map((_, i) => (i % 2 ? 3 : 61)),
    },
    daily: {
      time: ['2026-11-06', '2026-11-07', '2026-11-08', '2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12'],
      temperature_2m_max: [13, 10, 8, 12, 15, 9, 7],
      temperature_2m_min: [4, 2, -1, 3, 6, 1, -3],
      precipitation_probability_max: [20, 60, 10, 0, 5, 80, 30],
      weather_code: [2, 61, 3, 0, 1, 71, 3],
    },
  };
}

export function okResponse(body: unknown) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
}
