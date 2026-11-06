import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { weatherClient, WeatherClient } from '../api/openMeteo';
import type { Place } from '../domain/types';

interface Props {
  onSelect: (place: Place) => void;
  onUseMyLocation: () => void;
  client?: Pick<WeatherClient, 'searchPlaces'>;
  debounceMs?: number;
}

/**
 * City search with debouncing: we only hit the geocoding API once the user
 * pauses typing, and abort any request superseded by newer input.
 */
export function CitySearch({ onSelect, onUseMyLocation, client = weatherClient, debounceMs = 350 }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const places = await client.searchPlaces(query, controller.signal);
        if (!controller.signal.aborted) setResults(places);
      } catch {
        if (!controller.signal.aborted) setResults([]);
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, debounceMs);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, client, debounceMs]);

  const choose = (p: Place) => {
    setQuery('');
    setResults([]);
    onSelect(p);
  };

  return (
    <View>
      <View style={styles.bar}>
        <TextInput
          style={styles.input}
          placeholder="Search city…"
          placeholderTextColor="#9fb3d9"
          value={query}
          onChangeText={setQuery}
          autoCorrect={false}
          returnKeyType="search"
          accessibilityLabel="Search city"
        />
        <Pressable onPress={onUseMyLocation} style={styles.locate} accessibilityLabel="Use my location">
          <Text style={styles.locateText}>📍</Text>
        </Pressable>
      </View>
      {searching && <ActivityIndicator color="#fff" style={{ marginTop: 6 }} />}
      {results.map((p) => (
        <Pressable key={`${p.latitude},${p.longitude}`} onPress={() => choose(p)} style={styles.result}>
          <Text style={styles.resultText}>{p.name}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  input: { flex: 1, backgroundColor: 'rgba(255,255,255,0.18)', color: '#fff', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 16 },
  locate: { backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: 12, padding: 10 },
  locateText: { fontSize: 18 },
  result: { paddingVertical: 10, paddingHorizontal: 14, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: 'rgba(255,255,255,0.3)' },
  resultText: { color: '#fff', fontSize: 16 },
});
