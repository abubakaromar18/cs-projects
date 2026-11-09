<script setup>
import { computed } from 'vue';
import { formatDay } from '../lib/dates.js';
import { barGeometry, overallRange } from '../lib/tempRange.js';
import { formatPercent, formatTemperature } from '../lib/units.js';
import { describeWeather } from '../lib/weatherCodes.js';

const props = defineProps({
  days: { type: Array, required: true },
  unit: { type: String, required: true },
});

const rows = computed(() => {
  const range = overallRange(props.days);
  return props.days.map((day, index) => ({
    ...day,
    // With timezone=auto the first entry is "today" in the city itself.
    label: formatDay(day.date, { today: index === 0 }),
    weather: describeWeather(day.code),
    bar: barGeometry(day, range),
  }));
});
</script>

<template>
  <section class="card" aria-labelledby="forecast-heading">
    <h2 id="forecast-heading">{{ days.length }}-day forecast</h2>
    <ol class="forecast">
      <li v-for="row in rows" :key="row.date" class="day" data-test="day">
        <div class="day-label">
          <strong>{{ row.label.weekday }}</strong>
          <span class="muted">{{ row.label.date }}</span>
        </div>
        <div class="day-weather">
          <span aria-hidden="true">{{ row.weather.icon }}</span>
          <span>{{ row.weather.label }}</span>
        </div>
        <div class="day-rain">
          <span class="visually-hidden">Chance of rain: </span>
          <span aria-hidden="true">💧</span>
          {{ formatPercent(row.rainChance) }}
        </div>
        <div class="day-temps">
          <span class="muted">
            <span class="visually-hidden">Low: </span>{{ formatTemperature(row.low, unit) }}
          </span>
          <span class="bar-track" aria-hidden="true">
            <span
              v-if="row.bar"
              class="bar"
              :style="{ left: `${row.bar.left}%`, width: `${row.bar.width}%` }"
            ></span>
          </span>
          <span><span class="visually-hidden">High: </span>{{ formatTemperature(row.high, unit) }}</span>
        </div>
      </li>
    </ol>
  </section>
</template>
