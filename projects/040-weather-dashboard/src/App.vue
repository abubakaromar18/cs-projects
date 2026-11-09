<script setup>
import { onMounted, ref, watch } from 'vue';
import CitySearch from './components/CitySearch.vue';
import CurrentWeather from './components/CurrentWeather.vue';
import ForecastList from './components/ForecastList.vue';
import UnitToggle from './components/UnitToggle.vue';
import { fetchForecast } from './api/openMeteo.js';
import { useWeather } from './composables/useWeather.js';
import { loadCity, loadUnit, saveCity, saveUnit } from './lib/storage.js';

const unit = ref(loadUnit());
watch(unit, saveUnit);

const { city, forecast, status, errorMessage, load, retry } = useWeather(fetchForecast);

function selectCity(selected) {
  saveCity(selected);
  load(selected);
}

onMounted(() => {
  const saved = loadCity();
  if (saved) load(saved);
});
</script>

<template>
  <div class="page">
    <header class="top">
      <h1>Weather</h1>
      <UnitToggle v-model="unit" />
    </header>

    <CitySearch @select="selectCity" />

    <main>
      <p v-if="status === 'idle'" class="card notice">Search for a city to see its weather.</p>
      <p v-else-if="status === 'loading'" class="card notice" role="status">
        Loading weather for {{ city.name }}…
      </p>
      <div v-else-if="status === 'error'" class="card notice" role="alert">
        <p>{{ errorMessage }}</p>
        <button type="button" class="retry" @click="retry">Try again</button>
      </div>
      <template v-else>
        <CurrentWeather :city="city" :current="forecast.current" :unit="unit" />
        <ForecastList :days="forecast.days" :unit="unit" />
      </template>
    </main>

    <footer class="muted">
      Weather data by <a href="https://open-meteo.com/" rel="noopener">Open-Meteo</a> (CC BY 4.0)
    </footer>
  </div>
</template>
