# 033 · Weather App (React Native)

A location-based weather app built with **React Native + Expo + TypeScript**.
It finds your position, then shows current conditions, a 24-hour strip and a
7-day forecast. You can also search any city and switch between °C and °F.
Data comes from [Open-Meteo](https://open-meteo.com/), which is free and needs
**no API key**.

```
┌──────────────────────────────┐
│ [Search city…        ] [📍]  │
│                    °C → °F   │
│        Chicago, Illinois     │
│              ⛅              │
│             12°              │
│        Partly cloudy         │
│       H 13°  ·  L 4°         │
│ [Feels 9°][Hum 62%][18 km/h] │
│ NEXT 24 HOURS                │
│ Now  3PM  4PM  5PM  6PM  …   │
│ 🌧️   ☁️   🌧️   ☁️   🌧️       │
│ 12°  12°  13°  13°  14°      │
│ 7-DAY FORECAST               │
│ Today ⛅  4° ━━━━━━──── 13°  │
│ Sat   🌧️  2° ──━━━━──── 10°  │
│ …                            │
└──────────────────────────────┘
```

## Features

- 📍 Uses your location (foreground permission, coarse accuracy to save battery), with a reverse-geocoded place name
- 🔎 City search with a debounced geocoding lookup
- 🌡️ Current temperature, feels-like, humidity, wind
- ⏱️ Next 24 hours, starting at the current hour *in the location's own timezone*
- 📅 7-day forecast with high/low range bars scaled to the week
- 🔁 Pull-to-refresh that keeps showing the old forecast until the new one arrives
- °C/°F toggle (also switches km/h ↔ mph)
- Friendly errors (permission denied, offline, HTTP errors) with a retry button

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Finite state machine** via a pure reducer (`idle → loading → success/error`, plus refresh) | `src/hooks/weatherState.ts` |
| **TTL + LRU cache** using `Map` insertion order for O(1) recency updates | `src/api/cache.ts` |
| **Race-condition avoidance**: each request gets an `AbortController`; newer requests cancel older ones | `src/hooks/useWeather.ts`, `CitySearch.tsx` |
| **Debouncing** user input to limit network calls | `src/components/CitySearch.tsx` |
| **Anti-corruption layer**: raw JSON is validated and mapped into domain types | `src/api/openMeteo.ts` → `src/domain/types.ts` |
| **Dependency injection** (`fetch`, clock, location, client) for deterministic tests | throughout |
| **Lookup table** for WMO weather codes | `src/domain/weatherCodes.ts` |
| **Timezone-safe date handling** (parse `YYYY-MM-DD` components rather than `new Date(str)`) | `src/domain/format.ts` |
| **Linear interpolation** to position the min/max temperature bars | `src/components/DailyForecast.tsx` |
| **Cache key normalisation**: coordinates rounded to ~1 km so nearby lookups share entries | `buildForecastUrl` |

## Project structure

```
033-weather-app/
├── App.tsx                     # root component
├── app.json                    # Expo config (location permission text)
├── src/
│   ├── api/
│   │   ├── cache.ts            # TTL/LRU cache
│   │   └── openMeteo.ts        # URL builders, parsers, WeatherClient
│   ├── domain/
│   │   ├── types.ts            # Forecast, Place, Units…
│   │   ├── format.ts           # temperature/speed/date formatting
│   │   └── weatherCodes.ts     # WMO code → label + emoji
│   ├── hooks/
│   │   ├── location.ts         # expo-location wrapper
│   │   ├── weatherState.ts     # reducer / state machine
│   │   └── useWeather.ts       # orchestration hook
│   └── components/
│       ├── WeatherScreen.tsx   # screen layout + state rendering
│       ├── CitySearch.tsx
│       ├── CurrentWeather.tsx
│       ├── HourlyStrip.tsx
│       └── DailyForecast.tsx
├── __tests__/                  # Jest + React Native Testing Library
└── testing/                    # fixtures and Jest setup
```

## Build, run, test

Requires Node 18+.

```bash
npm install
npm start           # opens Expo dev tools; scan the QR code with Expo Go
npm run android     # or: npm run ios  (needs an emulator/simulator)
npm test            # 30 unit + component tests
npm run typecheck   # strict TypeScript
```

Tests run in Node via `jest-expo` and never touch the network: the API client
gets a fake `fetch`, the screen gets a fake `locate()` and client, and the
search test uses Jest fake timers to check debouncing.

```
PASS __tests__/WeatherScreen.test.tsx
PASS __tests__/format.test.ts
PASS __tests__/openMeteo.test.ts
PASS __tests__/weatherState.test.ts
PASS __tests__/cache.test.ts

Tests:       30 passed, 30 total
```

The app also bundles for Android with `npx expo export --platform android`.
It wasn't run on a device or emulator during development, and the live Open-Meteo
API couldn't be reached from the build environment, so the parsers are
tested against fixtures modelled on the
[documented response format](https://open-meteo.com/en/docs).

## Example API request

```
https://api.open-meteo.com/v1/forecast?latitude=41.88&longitude=-87.63
  &current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day
  &hourly=temperature_2m,precipitation_probability,weather_code
  &daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code
  &timezone=auto&forecast_days=7
```

## Possible extensions

- Save favourite cities with `AsyncStorage` and swipe between them
- Keep the last forecast on disk so the app opens instantly offline
- Background tint that follows the weather or time of day
- Charts for hourly temperature and precipitation (`react-native-svg`)
- Severe-weather alerts with push notifications
- Air quality and UV index from Open-Meteo's other endpoints
- Localisation (i18n) and locale-aware number/date formatting
