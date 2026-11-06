import { useCallback, useEffect, useReducer, useRef } from 'react';
import { weatherClient as defaultClient, WeatherClient } from '../api/openMeteo';
import type { Place, Units } from '../domain/types';
import { getCurrentPlace } from './location';
import { initialWeatherState, weatherReducer } from './weatherState';

interface Deps {
  client?: Pick<WeatherClient, 'getForecast'>;
  locate?: () => Promise<Place>;
}

function messageOf(e: unknown): string {
  return e instanceof Error ? e.message : 'Something went wrong.';
}

/**
 * Orchestrates location + forecast fetching. Each request gets its own
 * AbortController, and older in-flight requests are cancelled so a slow
 * response can never overwrite a newer one (avoids a classic race condition).
 */
export function useWeather(units: Units, deps: Deps = {}) {
  const client = deps.client ?? defaultClient;
  const locate = deps.locate ?? getCurrentPlace;
  const [state, dispatch] = useReducer(weatherReducer, initialWeatherState);
  const controllerRef = useRef<AbortController | null>(null);
  const placeRef = useRef<Place | undefined>(undefined);

  const load = useCallback(
    async (place: Place, opts: { refresh?: boolean } = {}) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      placeRef.current = place;
      dispatch(opts.refresh ? { type: 'REFRESH_START' } : { type: 'FETCH_START', place });
      try {
        const forecast = await client.getForecast(place, units, { signal: controller.signal, force: opts.refresh });
        if (!controller.signal.aborted) dispatch({ type: 'FETCH_SUCCESS', place, forecast });
      } catch (e) {
        if (!controller.signal.aborted) dispatch({ type: 'FETCH_ERROR', message: messageOf(e), place });
      }
    },
    [client, units],
  );

  const locateMe = useCallback(async () => {
    dispatch({ type: 'LOCATE_START' });
    try {
      await load(await locate());
    } catch (e) {
      dispatch({ type: 'FETCH_ERROR', message: messageOf(e) });
    }
  }, [load, locate]);

  const refresh = useCallback(() => {
    if (placeRef.current) return load(placeRef.current, { refresh: true });
    return locateMe();
  }, [load, locateMe]);

  // Initial load, and reload when units change.
  useEffect(() => {
    if (placeRef.current) load(placeRef.current);
    else locateMe();
    return () => controllerRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [units]);

  return { state, selectPlace: load, locateMe, refresh };
}
