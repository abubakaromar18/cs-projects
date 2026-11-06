import { parseForecast } from '../src/api/openMeteo';
import { initialWeatherState, weatherReducer, WeatherState } from '../src/hooks/weatherState';
import { makeRawForecast } from '../testing/fixtures';

const place = { name: 'Chicago', latitude: 41.88, longitude: -87.63 };
const forecast = parseForecast(makeRawForecast(), 'metric');

describe('weatherReducer', () => {
  it('goes idle -> loading -> success', () => {
    let s: WeatherState = weatherReducer(initialWeatherState, { type: 'FETCH_START', place });
    expect(s).toEqual({ status: 'loading', place });
    s = weatherReducer(s, { type: 'FETCH_SUCCESS', place, forecast });
    expect(s).toMatchObject({ status: 'success', refreshing: false });
  });

  it('keeps stale data while refreshing', () => {
    const success = weatherReducer(initialWeatherState, { type: 'FETCH_SUCCESS', place, forecast });
    const refreshing = weatherReducer(success, { type: 'REFRESH_START' });
    expect(refreshing).toMatchObject({ status: 'success', refreshing: true, forecast });
  });

  it('does not wipe a good forecast when a refresh fails', () => {
    const refreshing = weatherReducer(
      weatherReducer(initialWeatherState, { type: 'FETCH_SUCCESS', place, forecast }),
      { type: 'REFRESH_START' },
    );
    const after = weatherReducer(refreshing, { type: 'FETCH_ERROR', message: 'offline' });
    expect(after).toMatchObject({ status: 'success', refreshing: false });
  });

  it('shows an error when an initial load fails', () => {
    const s = weatherReducer({ status: 'loading', place }, { type: 'FETCH_ERROR', message: 'boom', place });
    expect(s).toEqual({ status: 'error', message: 'boom', place });
  });

  it('ignores refresh when there is nothing to refresh', () => {
    expect(weatherReducer(initialWeatherState, { type: 'REFRESH_START' })).toBe(initialWeatherState);
  });
});
