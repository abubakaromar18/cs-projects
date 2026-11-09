import { onScopeDispose, ref, shallowRef } from 'vue';

/**
 * Holds the forecast for the selected city.
 * status: 'idle' | 'loading' | 'ready' | 'error'
 *
 * Picking a new city clears the old forecast, so one city's numbers are never
 * shown under another's name. If cities are picked quickly, the last one wins.
 */
export function useWeather(fetchForecast) {
  const city = shallowRef(null);
  const forecast = shallowRef(null);
  const status = ref('idle');
  const errorMessage = ref('');

  let controller = null;

  async function load(nextCity) {
    controller?.abort();
    const current = new AbortController();
    controller = current;

    city.value = nextCity;
    forecast.value = null;
    status.value = 'loading';
    try {
      const data = await fetchForecast(nextCity, { signal: current.signal });
      if (controller !== current) return;
      forecast.value = data;
      status.value = 'ready';
    } catch (error) {
      if (controller !== current) return;
      errorMessage.value = error.message;
      status.value = 'error';
    }
  }

  function retry() {
    if (city.value) return load(city.value);
  }

  onScopeDispose(() => controller?.abort());

  return { city, forecast, status, errorMessage, load, retry };
}
