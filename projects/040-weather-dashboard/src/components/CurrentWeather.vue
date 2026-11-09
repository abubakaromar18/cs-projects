<script setup>
import { computed } from 'vue';
import { formatPercent, formatTemperature, formatWindSpeed } from '../lib/units.js';
import { describeWeather } from '../lib/weatherCodes.js';

const props = defineProps({
  city: { type: Object, required: true },
  current: { type: Object, required: true },
  unit: { type: String, required: true },
});

const weather = computed(() =>
  describeWeather(props.current.code, { isDay: props.current.isDay }),
);
const place = computed(() =>
  [props.city.region, props.city.country].filter(Boolean).join(', '),
);
</script>

<template>
  <section class="card current" aria-labelledby="current-heading">
    <div>
      <h2 id="current-heading">{{ city.name }}</h2>
      <p class="muted">{{ place }}</p>
    </div>
    <div class="current-main">
      <span class="current-icon" aria-hidden="true">{{ weather.icon }}</span>
      <div>
        <p class="current-temp" data-test="current-temp">
          {{ formatTemperature(current.temperature, unit, { showUnit: true }) }}
        </p>
        <p>{{ weather.label }}</p>
      </div>
    </div>
    <dl class="stats">
      <div>
        <dt>Feels like</dt>
        <dd>{{ formatTemperature(current.feelsLike, unit, { showUnit: true }) }}</dd>
      </div>
      <div>
        <dt>Humidity</dt>
        <dd>{{ formatPercent(current.humidity) }}</dd>
      </div>
      <div>
        <dt>Wind</dt>
        <dd data-test="wind">{{ formatWindSpeed(current.windSpeed, unit) }}</dd>
      </div>
    </dl>
  </section>
</template>
