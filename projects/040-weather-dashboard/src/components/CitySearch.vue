<script setup>
import { computed, ref, watch } from 'vue';
import { searchCities } from '../api/openMeteo.js';
import { useCitySearch } from '../composables/useCitySearch.js';

const emit = defineEmits(['select']);

const { query, results, status, errorMessage } = useCitySearch(searchCities);

const open = ref(false);
const activeIndex = ref(-1);

const message = computed(() => {
  if (status.value === 'loading') return 'Searching…';
  if (status.value === 'empty') return 'No cities found.';
  if (status.value === 'error') return errorMessage.value;
  return '';
});
const showList = computed(() => open.value && results.value.length > 0);
const showMessage = computed(() => open.value && message.value !== '');
const activeId = computed(() =>
  showList.value && activeIndex.value >= 0 ? `city-option-${activeIndex.value}` : undefined,
);

// Results changed, so the old highlight no longer points at the same city.
watch(results, () => {
  activeIndex.value = -1;
});

const describe = (city) => [city.region, city.country].filter(Boolean).join(', ');

function choose(city) {
  emit('select', city);
  query.value = '';
  open.value = false;
}

// Standard combobox keys: focus stays in the input while arrows move a
// virtual highlight, exposed to screen readers by aria-activedescendant.
function move(delta) {
  open.value = true;
  const count = results.value.length;
  if (count) activeIndex.value = (activeIndex.value + delta + count) % count;
}

function moveUp() {
  // From "nothing highlighted", ArrowUp wraps to the last result.
  if (activeIndex.value === -1) activeIndex.value = 0;
  move(-1);
}

function onEnter() {
  // Enter with no highlight takes the top match, the usual search-box shortcut.
  const city = results.value[Math.max(activeIndex.value, 0)];
  if (showList.value && city) choose(city);
}
</script>

<template>
  <div class="search">
    <label class="visually-hidden" for="city-input">Search for a city</label>
    <input
      id="city-input"
      v-model="query"
      type="search"
      role="combobox"
      placeholder="Search for a city…"
      autocomplete="off"
      spellcheck="false"
      aria-autocomplete="list"
      aria-controls="city-options"
      :aria-expanded="showList"
      :aria-activedescendant="activeId"
      @input="open = true"
      @focus="open = true"
      @blur="open = false"
      @keydown.down.prevent="move(1)"
      @keydown.up.prevent="moveUp"
      @keydown.enter.prevent="onEnter"
      @keydown.esc="open = false"
    />
    <!-- mousedown is prevented so the input keeps focus until click selects. -->
    <ul v-show="showList" id="city-options" class="search-panel" role="listbox" aria-label="Cities">
      <li
        v-for="(city, index) in results"
        :id="`city-option-${index}`"
        :key="city.id"
        role="option"
        :aria-selected="index === activeIndex"
        :class="{ active: index === activeIndex }"
        @mousedown.prevent
        @mousemove="activeIndex = index"
        @click="choose(city)"
      >
        <span class="city-name">{{ city.name }}</span>
        <span class="city-place">{{ describe(city) }}</span>
      </li>
    </ul>
    <p v-if="showMessage" class="search-panel search-message" role="status">{{ message }}</p>
  </div>
</template>
