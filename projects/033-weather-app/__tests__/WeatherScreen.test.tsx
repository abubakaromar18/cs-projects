import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import React from 'react';
import { parseForecast } from '../src/api/openMeteo';
import { CitySearch } from '../src/components/CitySearch';
import { WeatherScreen } from '../src/components/WeatherScreen';
import type { Place, Units } from '../src/domain/types';
import { makeRawForecast } from '../testing/fixtures';

// expo-location is native; the screen gets an injected `locate` instead.
jest.mock('expo-location', () => ({}));

const chicago: Place = { name: 'Chicago, Illinois', latitude: 41.88, longitude: -87.63 };

function fakeClient() {
  return {
    getForecast: jest.fn(async (_p: Place, units: Units) => {
      const raw = makeRawForecast();
      if (units === 'imperial') raw.current.temperature_2m = 52.9;
      return parseForecast(raw, units);
    }),
  };
}

describe('WeatherScreen', () => {
  it('locates the user and renders the forecast', async () => {
    const client = fakeClient();
    render(<WeatherScreen deps={{ client, locate: async () => chicago }} />);

    expect(screen.getByTestId('loading')).toBeTruthy();
    expect(await screen.findByText('Chicago, Illinois')).toBeTruthy();
    expect(screen.getByTestId('current-temp')).toHaveTextContent('12°');
    expect(screen.getByText('Partly cloudy')).toBeTruthy();
    expect(screen.getAllByTestId('day-row')).toHaveLength(7);
    expect(screen.getByText('Today')).toBeTruthy();
    expect(screen.getByText('Now')).toBeTruthy();
  });

  it('refetches in imperial units when toggled', async () => {
    const client = fakeClient();
    render(<WeatherScreen deps={{ client, locate: async () => chicago }} />);
    await screen.findByText('Chicago, Illinois');

    fireEvent.press(screen.getByLabelText('Toggle units'));
    await waitFor(() => expect(screen.getByTestId('current-temp')).toHaveTextContent('53°'));
    expect(client.getForecast).toHaveBeenLastCalledWith(chicago, 'imperial', expect.any(Object));
  });

  it('shows a helpful error when location permission is denied, and retries', async () => {
    const client = fakeClient();
    const locate = jest
      .fn()
      .mockRejectedValueOnce(new Error('Location permission denied. Search for a city instead.'))
      .mockResolvedValueOnce(chicago);
    render(<WeatherScreen deps={{ client, locate }} />);

    expect(await screen.findByText(/permission denied/)).toBeTruthy();
    fireEvent.press(screen.getByText('Try again'));
    expect(await screen.findByText('Chicago, Illinois')).toBeTruthy();
  });
});

describe('CitySearch', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('debounces input and lets the user pick a result', async () => {
    const searchPlaces = jest.fn(async () => [{ name: 'Paris, Île-de-France, FR', latitude: 48.85, longitude: 2.35 }]);
    const onSelect = jest.fn();
    render(<CitySearch client={{ searchPlaces }} onSelect={onSelect} onUseMyLocation={() => {}} debounceMs={300} />);

    const input = screen.getByLabelText('Search city');
    fireEvent.changeText(input, 'Pa');
    fireEvent.changeText(input, 'Par');
    fireEvent.changeText(input, 'Paris');
    expect(searchPlaces).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(300);
    });
    expect(searchPlaces).toHaveBeenCalledTimes(1);
    expect(searchPlaces).toHaveBeenCalledWith('Paris', expect.anything());

    fireEvent.press(await screen.findByText('Paris, Île-de-France, FR'));
    expect(onSelect).toHaveBeenCalledWith({ name: 'Paris, Île-de-France, FR', latitude: 48.85, longitude: 2.35 });
  });
});
