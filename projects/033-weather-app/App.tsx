import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { WeatherScreen } from './src/components/WeatherScreen';

export default function App() {
  return (
    <View style={styles.root}>
      <StatusBar style="light" />
      <WeatherScreen />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#2b5ba8' },
});
