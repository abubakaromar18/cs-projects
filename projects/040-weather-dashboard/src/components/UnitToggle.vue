<script setup>
import { UNITS } from '../lib/units.js';

const unit = defineModel({ type: String, required: true });
const options = [
  { value: UNITS.METRIC, label: '°C', name: 'Celsius' },
  { value: UNITS.IMPERIAL, label: '°F', name: 'Fahrenheit' },
];
</script>

<template>
  <div class="unit-toggle" role="group" aria-label="Temperature unit">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-label="option.name"
      :aria-pressed="unit === option.value"
      @click="unit = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>
