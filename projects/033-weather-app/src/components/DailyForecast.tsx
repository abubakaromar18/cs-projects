import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { formatTemperature, formatWeekday } from '../domain/format';
import type { DailyPoint, Units } from '../domain/types';
import { weatherIcon } from '../domain/weatherCodes';

interface Props {
  days: DailyPoint[];
  units: Units;
  todayIso?: string;
}

/**
 * 7-day list with a min/max temperature bar scaled to the week's range,
 * like the iOS weather app: the bar's offset and width are linear maps of
 * the day's low/high onto [weekMin, weekMax].
 */
export function DailyForecast({ days, units, todayIso }: Props) {
  const weekMin = Math.min(...days.map((d) => d.low));
  const weekMax = Math.max(...days.map((d) => d.high));
  const span = Math.max(weekMax - weekMin, 1);

  return (
    <View style={styles.card}>
      <Text style={styles.title}>7-day forecast</Text>
      {days.map((d) => {
        const left = ((d.low - weekMin) / span) * 100;
        const width = Math.max(((d.high - d.low) / span) * 100, 4);
        return (
          <View key={d.date} style={styles.row} testID="day-row">
            <Text style={styles.day}>{formatWeekday(d.date, todayIso)}</Text>
            <Text style={styles.icon}>{weatherIcon(d.weatherCode)}</Text>
            <Text style={styles.low}>{formatTemperature(d.low, units)}</Text>
            <View style={styles.track}>
              <View style={[styles.bar, { left: `${left}%`, width: `${width}%` }]} />
            </View>
            <Text style={styles.high}>{formatTemperature(d.high, units)}</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 16, padding: 12, marginTop: 12 },
  title: { color: '#cfe0ff', fontSize: 13, marginBottom: 4, textTransform: 'uppercase' },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  day: { color: '#fff', fontSize: 16, width: 56 },
  icon: { fontSize: 20, width: 36, textAlign: 'center' },
  low: { color: '#cfe0ff', fontSize: 16, width: 40, textAlign: 'right' },
  track: { flex: 1, height: 6, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.2)', marginHorizontal: 10 },
  bar: { position: 'absolute', top: 0, bottom: 0, borderRadius: 3, backgroundColor: '#ffd36e' },
  high: { color: '#fff', fontSize: 16, width: 40 },
});
