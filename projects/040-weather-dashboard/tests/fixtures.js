export const BERLIN = {
  id: 2950159,
  name: 'Berlin',
  region: 'Land Berlin',
  country: 'Germany',
  latitude: 52.52,
  longitude: 13.41,
};

export const geocodingBody = {
  results: [
    {
      id: 2950159,
      name: 'Berlin',
      latitude: 52.52,
      longitude: 13.41,
      country: 'Germany',
      admin1: 'Land Berlin',
    },
    { id: 5083330, name: 'Berlin', latitude: 44.47, longitude: -71.19, country: 'United States', admin1: 'New Hampshire' },
  ],
};

export const forecastBody = {
  timezone: 'Europe/Berlin',
  current: {
    temperature_2m: 20,
    apparent_temperature: 18.4,
    relative_humidity_2m: 55,
    wind_speed_10m: 16.09344,
    weather_code: 2,
    is_day: 1,
  },
  daily: {
    time: ['2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12', '2026-11-13'],
    weather_code: [2, 61, 3, 0, 95],
    temperature_2m_max: [20, 15, 10, 12, 18],
    temperature_2m_min: [10, 8, 0, 2, 9],
    precipitation_probability_max: [10, 80, null, 0, 65],
  },
};

export function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

export function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
