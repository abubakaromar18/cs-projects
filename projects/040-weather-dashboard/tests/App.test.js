import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import App from '../src/App.vue';
import { BERLIN, forecastBody, geocodingBody, jsonResponse } from './fixtures.js';

// Exercises the real components and API client; only the network is fake.
function stubNetwork({ forecast = () => jsonResponse(forecastBody) } = {}) {
  const fetchMock = vi.fn(async (url) => {
    if (url.includes('geocoding-api')) {
      return new URL(url).searchParams.get('name') === 'zzz'
        ? jsonResponse({})
        : jsonResponse(geocodingBody);
    }
    return forecast();
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const forecastCalls = (fetchMock) =>
  fetchMock.mock.calls.filter(([url]) => url.includes('/v1/forecast'));

async function typeCity(wrapper, text) {
  await wrapper.find('input').setValue(text);
  vi.advanceTimersByTime(250);
  await flushPromises();
}

describe('App', () => {
  let wrapper;

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  async function searchAndPick(text = 'Berlin') {
    await typeCity(wrapper, text);
    await wrapper.findAll('[role="option"]')[0].trigger('click');
    await flushPromises();
  }

  it('prompts for a city on first visit', () => {
    stubNetwork();
    wrapper = mount(App);
    expect(wrapper.text()).toContain('Search for a city to see its weather');
  });

  it('searches, then shows current weather and five days', async () => {
    stubNetwork();
    wrapper = mount(App);
    await wrapper.find('input').trigger('focus');
    await typeCity(wrapper, 'Berlin');
    const options = wrapper.findAll('[role="option"]');
    expect(options).toHaveLength(2);
    expect(options[1].text()).toContain('New Hampshire');

    await options[0].trigger('click');
    await flushPromises();
    expect(wrapper.find('#current-heading').text()).toBe('Berlin');
    expect(wrapper.find('[data-test="current-temp"]').text()).toBe('20°C');
    const days = wrapper.findAll('[data-test="day"]');
    expect(days).toHaveLength(5);
    expect(days[0].text()).toContain('Today');
    expect(days[1].text()).toContain('Tue');
    expect(wrapper.find('input').element.value).toBe('');
  });

  it('switches units without another request and remembers the choice', async () => {
    const fetchMock = stubNetwork();
    wrapper = mount(App);
    await searchAndPick();
    expect(forecastCalls(fetchMock)).toHaveLength(1);

    await wrapper.find('button[aria-label="Fahrenheit"]').trigger('click');
    expect(wrapper.find('[data-test="current-temp"]').text()).toBe('68°F');
    expect(wrapper.find('[data-test="wind"]').text()).toBe('10 mph');
    expect(wrapper.find('[data-test="day"]').text()).toContain('68°');
    expect(forecastCalls(fetchMock)).toHaveLength(1);
    await flushPromises();
    expect(localStorage.getItem('weather-dashboard:unit')).toBe('imperial');
  });

  it('restores the last city on load', async () => {
    const fetchMock = stubNetwork();
    localStorage.setItem('weather-dashboard:city', JSON.stringify(BERLIN));
    wrapper = mount(App);
    await flushPromises();
    expect(forecastCalls(fetchMock)).toHaveLength(1);
    expect(wrapper.find('#current-heading').text()).toBe('Berlin');
  });

  it('supports keyboard selection with wrap-around', async () => {
    stubNetwork();
    wrapper = mount(App);
    const input = wrapper.find('input');
    await input.trigger('focus');
    await typeCity(wrapper, 'Berlin');

    await input.trigger('keydown', { key: 'ArrowUp' });
    expect(input.attributes('aria-activedescendant')).toBe('city-option-1');
    await input.trigger('keydown', { key: 'ArrowDown' });
    expect(input.attributes('aria-activedescendant')).toBe('city-option-0');
    await input.trigger('keydown', { key: 'ArrowDown' });
    await input.trigger('keydown', { key: 'Enter' });
    await flushPromises();
    expect(wrapper.text()).toContain('New Hampshire');
  });

  it('closes suggestions on Escape, and Enter then does nothing', async () => {
    const fetchMock = stubNetwork();
    wrapper = mount(App);
    const input = wrapper.find('input');
    await input.trigger('focus');
    await typeCity(wrapper, 'Berlin');
    expect(input.attributes('aria-expanded')).toBe('true');
    await input.trigger('keydown', { key: 'Escape' });
    expect(input.attributes('aria-expanded')).toBe('false');
    await input.trigger('keydown', { key: 'Enter' });
    await flushPromises();
    expect(forecastCalls(fetchMock)).toHaveLength(0);
  });

  it('says when no city matches', async () => {
    stubNetwork();
    wrapper = mount(App);
    await wrapper.find('input').trigger('focus');
    await typeCity(wrapper, 'zzz');
    expect(wrapper.find('[role="status"]').text()).toBe('No cities found.');
  });

  it('shows an error and recovers on retry', async () => {
    let healthy = false;
    stubNetwork({
      forecast: () =>
        healthy ? jsonResponse(forecastBody) : jsonResponse({ error: true, reason: 'Busy' }, 500),
    });
    wrapper = mount(App);
    await searchAndPick();
    expect(wrapper.find('[role="alert"]').text()).toContain('Busy');

    healthy = true;
    await wrapper.find('.retry').trigger('click');
    await flushPromises();
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="current-temp"]').text()).toBe('20°C');
  });

  it('renders user-visible placeholders for missing readings', async () => {
    const sparse = structuredClone(forecastBody);
    sparse.current.temperature_2m = null;
    stubNetwork({ forecast: () => jsonResponse(sparse) });
    wrapper = mount(App);
    await searchAndPick();
    expect(wrapper.find('[data-test="current-temp"]').text()).toBe('–');
    expect(wrapper.findAll('[data-test="day"]')[2].text()).toContain('–');
  });
});
