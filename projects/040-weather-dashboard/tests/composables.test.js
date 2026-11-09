import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';
import { useCitySearch } from '../src/composables/useCitySearch.js';
import { useWeather } from '../src/composables/useWeather.js';
import { BERLIN, deferred } from './fixtures.js';

const PARIS = { ...BERLIN, id: 2, name: 'Paris' };

// Run a composable inside a scope, as a component would.
function inScope(factory) {
  const scope = effectScope();
  return { api: scope.run(factory), scope };
}

describe('useCitySearch', () => {
  beforeEach(() => vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] }));
  afterEach(() => vi.useRealTimers());

  async function type(api, text) {
    api.query.value = text;
    await nextTick();
  }

  it('debounces keystrokes into one request', async () => {
    const search = vi.fn(async () => [BERLIN]);
    const { api } = inScope(() => useCitySearch(search));
    await type(api, 'Be');
    vi.advanceTimersByTime(100);
    await type(api, 'Ber');
    vi.advanceTimersByTime(100);
    await type(api, 'Berl');
    expect(search).not.toHaveBeenCalled();
    vi.advanceTimersByTime(250);
    await flushPromises();
    expect(search).toHaveBeenCalledTimes(1);
    expect(search.mock.calls[0][0]).toBe('Berl');
    expect(api.status.value).toBe('ready');
  });

  it('ignores queries that are too short', async () => {
    const search = vi.fn(async () => []);
    const { api } = inScope(() => useCitySearch(search));
    await type(api, ' B ');
    vi.advanceTimersByTime(1000);
    expect(search).not.toHaveBeenCalled();
    expect(api.status.value).toBe('idle');
  });

  it('never lets a slow old response overwrite a newer one', async () => {
    const first = deferred();
    const second = deferred();
    const search = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { api } = inScope(() => useCitySearch(search));

    await type(api, 'Ber');
    vi.advanceTimersByTime(250);
    await type(api, 'Par');
    vi.advanceTimersByTime(250);
    expect(search.mock.calls[0][1].signal.aborted).toBe(true);

    second.resolve([PARIS]);
    await flushPromises();
    first.resolve([BERLIN]);
    await flushPromises();
    expect(api.results.value).toEqual([PARIS]);
  });

  it('drops an in-flight response when the input is cleared', async () => {
    const pending = deferred();
    const { api } = inScope(() => useCitySearch(vi.fn(() => pending.promise)));
    await type(api, 'Ber');
    vi.advanceTimersByTime(250);
    await type(api, '');
    pending.resolve([BERLIN]);
    await flushPromises();
    expect(api.results.value).toEqual([]);
    expect(api.status.value).toBe('idle');
  });

  it('reports empty results and errors', async () => {
    const search = vi
      .fn()
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('Service down'));
    const { api } = inScope(() => useCitySearch(search));
    await type(api, 'zzz');
    vi.advanceTimersByTime(250);
    await flushPromises();
    expect(api.status.value).toBe('empty');
    await type(api, 'zzzz');
    vi.advanceTimersByTime(250);
    await flushPromises();
    expect(api.status.value).toBe('error');
    expect(api.errorMessage.value).toBe('Service down');
  });

  it('cancels pending work when its scope ends', async () => {
    const search = vi.fn(async () => []);
    const { api, scope } = inScope(() => useCitySearch(search));
    await type(api, 'Berlin');
    scope.stop();
    vi.advanceTimersByTime(1000);
    expect(search).not.toHaveBeenCalled();
  });
});

describe('useWeather', () => {
  const data = (name) => ({ current: {}, days: [], name });

  it('loads a forecast', async () => {
    const { api } = inScope(() => useWeather(vi.fn(async () => data('b'))));
    const loading = api.load(BERLIN);
    expect(api.status.value).toBe('loading');
    await loading;
    expect(api.status.value).toBe('ready');
    expect(api.forecast.value.name).toBe('b');
  });

  it('lets the most recent city win', async () => {
    const slow = deferred();
    const fast = deferred();
    const fetcher = vi.fn().mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);
    const { api } = inScope(() => useWeather(fetcher));
    api.load(BERLIN);
    api.load(PARIS);
    expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);
    fast.resolve(data('paris'));
    await flushPromises();
    slow.resolve(data('berlin'));
    await flushPromises();
    expect(api.city.value.name).toBe('Paris');
    expect(api.forecast.value.name).toBe('paris');
  });

  it('clears the old forecast when switching cities', async () => {
    const pending = deferred();
    const fetcher = vi.fn().mockResolvedValueOnce(data('b')).mockReturnValueOnce(pending.promise);
    const { api } = inScope(() => useWeather(fetcher));
    await api.load(BERLIN);
    api.load(PARIS);
    expect(api.forecast.value).toBeNull();
  });

  it('retries the same city after an error', async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error('Nope'))
      .mockResolvedValueOnce(data('b'));
    const { api } = inScope(() => useWeather(fetcher));
    await api.load(BERLIN);
    expect(api.status.value).toBe('error');
    expect(api.errorMessage.value).toBe('Nope');
    await api.retry();
    expect(fetcher).toHaveBeenLastCalledWith(BERLIN, expect.anything());
    expect(api.status.value).toBe('ready');
  });
});
