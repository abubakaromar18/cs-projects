import React from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';
import { formatHour, formatTemperature } from '../domain/format';
import type { HourlyPoint, Units } from '../domain/types';
import { weatherIcon } from '../domain/weatherCodes';

export function HourlyStrip({ hours, units }: { hours: HourlyPoint[]; units: Units }) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Next 24 hours</Text>
      <FlatList
        horizontal
        data={hours}
        keyExtractor={(h) => h.time}
        showsHorizontalScrollIndicator={false}
        renderItem={({ item, index }) => (
          <View style={styles.cell} testID="hour-cell">
            <Text style={styles.hour}>{index === 0 ? 'Now' : formatHour(item.time)}</Text>
            <Text style={styles.icon}>{weatherIcon(item.weatherCode)}</Text>
            <Text style={styles.temp}>{formatTemperature(item.temperature, units)}</Text>
            {item.precipitationProbability >= 20 && (
              <Text style={styles.rain}>{item.precipitationProbability}%</Text>
            )}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 16, padding: 12, marginTop: 12 },
  title: { color: '#cfe0ff', fontSize: 13, marginBottom: 8, textTransform: 'uppercase' },
  cell: { alignItems: 'center', width: 56 },
  hour: { color: '#fff', fontSize: 13 },
  icon: { fontSize: 22, marginVertical: 4 },
  temp: { color: '#fff', fontSize: 16, fontWeight: '600' },
  rain: { color: '#9fd3ff', fontSize: 11 },
});
