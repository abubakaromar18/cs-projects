/**
 * Thin wrapper over expo-location: asks for foreground permission, gets a
 * coarse position (enough for weather, cheaper on battery), and tries to
 * reverse-geocode it into a friendly name.
 */
import * as Location from 'expo-location';
import type { Place } from '../domain/types';

export class LocationPermissionError extends Error {
  constructor() {
    super('Location permission denied. Search for a city instead.');
    this.name = 'LocationPermissionError';
  }
}

export async function getCurrentPlace(): Promise<Place> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status !== 'granted') throw new LocationPermissionError();

  const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
  const { latitude, longitude } = pos.coords;

  let name = `${latitude.toFixed(2)}, ${longitude.toFixed(2)}`;
  try {
    const [addr] = await Location.reverseGeocodeAsync({ latitude, longitude });
    const label = [addr?.city ?? addr?.subregion, addr?.region].filter(Boolean).join(', ');
    if (label) name = label;
  } catch {
    // Reverse geocoding is a nicety; fall back to coordinates.
  }
  return { latitude, longitude, name };
}
