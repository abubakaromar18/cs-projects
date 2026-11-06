/** Core domain types, decoupled from the raw API response shape. */

export type Units = 'metric' | 'imperial';

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface Place extends Coordinates {
  /** Human-readable name, e.g. "Chicago, Illinois, US". */
  name: string;
}

export interface CurrentConditions {
  time: string; // ISO local time
  temperature: number;
  apparentTemperature: number;
  humidity: number; // percent
  windSpeed: number;
  weatherCode: number;
  isDay: boolean;
}

export interface HourlyPoint {
  time: string;
  temperature: number;
  precipitationProbability: number;
  weatherCode: number;
}

export interface DailyPoint {
  date: string; // YYYY-MM-DD
  high: number;
  low: number;
  precipitationProbability: number;
  weatherCode: number;
}

export interface Forecast {
  timezone: string;
  units: Units;
  current: CurrentConditions;
  hourly: HourlyPoint[];
  daily: DailyPoint[];
}
