# Weather Dashboard

A Vue 3 single-page app for checking the weather anywhere. Search for a city, see current conditions and a 5-day forecast, and switch between metric and imperial units. Data comes from [Open-Meteo](https://open-meteo.com/), which needs no API key.

## Features

- Search-as-you-type city lookup, with region and country to tell same-named places apart
- Current temperature, feels-like, humidity and wind
- 5-day forecast with chance of rain and low-to-high bars on a shared scale
- °C/°F toggle that also switches wind between km/h and mph, with no extra request
- Remembers your unit and last city
- Keyboard and screen-reader support, plus light and dark themes

## CS concepts

- **Race conditions in async UI:** a slow response must not overwrite a newer one. Each new request aborts the last, and a result is applied only if its request is still the latest (`src/composables/`).
- **Debouncing:** typing produces one request after a 250 ms pause rather than one per keystroke.
- **Reactive state and composables:** Vue's Composition API keeps request logic in `useCitySearch` and `useWeather`, separate from rendering.
- **Separating data from presentation:** the app stores canonical metric values and converts them only when displaying, so there is one source of truth.
- **Anti-corruption layer:** only `src/api/openMeteo.js` knows the wire format. It turns parallel daily arrays into one object per day and turns failures into readable errors.
- **Time zone handling:** `new Date("2026-11-09")` means midnight UTC, which is the previous day in the Americas. `src/lib/dates.js` keeps the city's calendar date intact.
- **Accessibility:** the search box follows the WAI-ARIA combobox pattern, using `aria-activedescendant` so focus stays in the input.
- **Defensive input handling:** `localStorage` can throw or hold corrupt data, and the app falls back to defaults in both cases.

## Build, run and test

Requires Node 20.19 or newer.

```sh
npm install

npm run dev       # development server at http://localhost:5173
npm test          # unit and component tests (Vitest)
npm run build     # production build in dist/
npm run preview   # serve the production build
```

The tests use a fake network, so they run offline. They were all run during development, along with a browser check of the production build at desktop and phone widths. That browser check also used mocked API responses, because the build environment could not reach Open-Meteo. The request format follows the Open-Meteo documentation but has not been exercised against the live service.

## Example

```text
Weather                                  [°C] [°F]

Berlin
Land Berlin, Germany
⛅ 20°C  Partly cloudy
Feels like 18°C · Humidity 55% · Wind 16 km/h

5-day forecast
Today  Nov 9   ⛅ Partly cloudy  💧10%  10° ━━━ 20°
Tue    Nov 10  🌦️ Light rain     💧80%   8° ━━  15°
Wed    Nov 11  ☁️ Overcast       💧–     0° ━━  10°
```

## Project layout

```text
src/
  api/openMeteo.js   HTTP client, response parsing, error handling
  composables/       useCitySearch (debounce, cancellation), useWeather
  components/        CitySearch, CurrentWeather, ForecastList, UnitToggle
  lib/               units, weather codes, dates, temperature bars, storage
tests/               API, library, composable and full-app tests
```

## Possible extensions

- "Use my location" through the Geolocation API
- Saved favourite cities
- Hourly forecast with a temperature chart
- Offline support with a service worker and cached forecasts
- Localised labels using Open-Meteo's `language` parameter and `Intl`
