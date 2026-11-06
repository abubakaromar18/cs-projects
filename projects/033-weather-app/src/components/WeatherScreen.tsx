import React, { useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useWeather } from '../hooks/useWeather';
import type { Units } from '../domain/types';
import { CitySearch } from './CitySearch';
import { CurrentWeather } from './CurrentWeather';
import { DailyForecast } from './DailyForecast';
import { HourlyStrip } from './HourlyStrip';

type Deps = Parameters<typeof useWeather>[1];

/** Top-level screen: search bar, units toggle, and the state-driven body. */
export function WeatherScreen({ deps, searchClient }: { deps?: Deps; searchClient?: React.ComponentProps<typeof CitySearch>['client'] }) {
  const [units, setUnits] = useState<Units>('metric');
  const { state, selectPlace, locateMe, refresh } = useWeather(units, deps);

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      refreshControl={
        <RefreshControl
          refreshing={state.status === 'success' && state.refreshing}
          onRefresh={refresh}
          tintColor="#fff"
        />
      }
    >
      <CitySearch onSelect={selectPlace} onUseMyLocation={locateMe} client={searchClient} />

      <Pressable
        onPress={() => setUnits((u) => (u === 'metric' ? 'imperial' : 'metric'))}
        style={styles.unitToggle}
        accessibilityLabel="Toggle units"
      >
        <Text style={styles.unitText}>{units === 'metric' ? '°C  →  °F' : '°F  →  °C'}</Text>
      </Pressable>

      {(state.status === 'idle' || state.status === 'loading') && (
        <View style={styles.center} testID="loading">
          <ActivityIndicator size="large" color="#fff" />
          <Text style={styles.muted}>{state.status === 'loading' && state.place ? `Loading ${state.place.name}…` : 'Finding your location…'}</Text>
        </View>
      )}

      {state.status === 'error' && (
        <View style={styles.center} testID="error">
          <Text style={styles.error}>{state.message}</Text>
          <Pressable onPress={refresh} style={styles.retry}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      )}

      {state.status === 'success' && (
        <>
          <CurrentWeather
            placeName={state.place.name}
            current={state.forecast.current}
            today={state.forecast.daily[0]}
            units={units}
          />
          <HourlyStrip hours={state.forecast.hourly} units={units} />
          <DailyForecast days={state.forecast.daily} units={units} todayIso={state.forecast.current.time.slice(0, 10)} />
          <Text style={styles.credit}>Weather data by Open-Meteo.com</Text>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, paddingTop: 56, paddingBottom: 40 },
  center: { alignItems: 'center', marginTop: 60, gap: 12 },
  muted: { color: '#cfe0ff' },
  error: { color: '#ffd6d6', fontSize: 16, textAlign: 'center' },
  retry: { backgroundColor: '#fff', borderRadius: 20, paddingHorizontal: 18, paddingVertical: 8 },
  retryText: { color: '#2b5ba8', fontWeight: '600' },
  unitToggle: { alignSelf: 'flex-end', marginTop: 10, padding: 6 },
  unitText: { color: '#fff', fontSize: 14 },
  credit: { color: '#9fb3d9', fontSize: 11, textAlign: 'center', marginTop: 16 },
});
