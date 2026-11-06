/**
 * Screen state modelled as a finite state machine via a pure reducer.
 * Keeping transitions pure means every edge case (stale data during refresh,
 * errors after a success, etc.) can be unit tested without rendering.
 */
import type { Forecast, Place } from '../domain/types';

export type WeatherState =
  | { status: 'idle' }
  | { status: 'loading'; place?: Place }
  | { status: 'success'; place: Place; forecast: Forecast; refreshing: boolean }
  | { status: 'error'; message: string; place?: Place };

export type WeatherAction =
  | { type: 'LOCATE_START' }
  | { type: 'FETCH_START'; place: Place }
  | { type: 'FETCH_SUCCESS'; place: Place; forecast: Forecast }
  | { type: 'FETCH_ERROR'; message: string; place?: Place }
  | { type: 'REFRESH_START' };

export const initialWeatherState: WeatherState = { status: 'idle' };

export function weatherReducer(state: WeatherState, action: WeatherAction): WeatherState {
  switch (action.type) {
    case 'LOCATE_START':
      return { status: 'loading' };
    case 'FETCH_START':
      return { status: 'loading', place: action.place };
    case 'REFRESH_START':
      // Keep showing the old forecast while refreshing (stale-while-revalidate).
      return state.status === 'success' ? { ...state, refreshing: true } : state;
    case 'FETCH_SUCCESS':
      return { status: 'success', place: action.place, forecast: action.forecast, refreshing: false };
    case 'FETCH_ERROR':
      // A failed background refresh should not wipe a good forecast.
      if (state.status === 'success' && state.refreshing) return { ...state, refreshing: false };
      return { status: 'error', message: action.message, place: action.place };
    default:
      return state;
  }
}
