import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { formatSpeed, formatTemperature } from '../domain/format';
import type { CurrentConditions, DailyPoint, Units } from '../domain/types';
import { describeWeather, weatherIcon } from '../domain/weatherCodes';

interface Props {
  placeName: string;
  current: CurrentConditions;
  today?: DailyPoint;
  units: Units;
}

export function CurrentWeather({ placeName, current, today, units }: Props) {
  const { label } = describeWeather(current.weatherCode);
  return (
    <View style={styles.container} accessibilityRole="summary">
      <Text style={styles.place} testID="place-name">{placeName}</Text>
      <Text style={styles.icon}>{weatherIcon(current.weatherCode, current.isDay)}</Text>
      <Text style={styles.temp} testID="current-temp">{formatTemperature(current.temperature, units)}</Text>
      <Text style={styles.label}>{label}</Text>
      {today && (
        <Text style={styles.sub}>
          H {formatTemperature(today.high, units)}  ·  L {formatTemperature(today.low, units)}
        </Text>
      )}
      <View style={styles.row}>
        <Stat title="Feels like" value={formatTemperature(current.apparentTemperature, units)} />
        <Stat title="Humidity" value={`${Math.round(current.humidity)}%`} />
        <Stat title="Wind" value={formatSpeed(current.windSpeed, units)} />
      </View>
    </View>
  );
}

function Stat({ title, value }: { title: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statTitle}>{title}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', paddingVertical: 16 },
  place: { fontSize: 22, fontWeight: '600', color: '#fff' },
  icon: { fontSize: 64, marginVertical: 4 },
  temp: { fontSize: 72, fontWeight: '200', color: '#fff' },
  label: { fontSize: 18, color: '#e0ecff' },
  sub: { fontSize: 16, color: '#e0ecff', marginTop: 4 },
  row: { flexDirection: 'row', marginTop: 16, gap: 12 },
  stat: { backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 12, padding: 10, minWidth: 90, alignItems: 'center' },
  statTitle: { fontSize: 12, color: '#cfe0ff' },
  statValue: { fontSize: 16, color: '#fff', fontWeight: '600' },
});
