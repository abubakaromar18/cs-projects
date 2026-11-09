import { onScopeDispose, ref, watch } from 'vue';

/**
 * Debounced search-as-you-type.
 *
 * Responses can arrive out of order, so each keystroke aborts the previous
 * request, and a result is applied only if its request is still the latest.
 *
 * status: 'idle' | 'loading' | 'ready' | 'empty' | 'error'
 */
export function useCitySearch(search, { debounceMs = 250, minLength = 2 } = {}) {
  const query = ref('');
  const results = ref([]);
  const status = ref('idle');
  const errorMessage = ref('');

  let timer;
  let controller = null;

  function cancelPending() {
    clearTimeout(timer);
    controller?.abort();
    controller = null;
  }

  async function run(term) {
    const current = new AbortController();
    controller = current;
    try {
      const found = await search(term, { signal: current.signal });
      if (controller !== current) return;
      results.value = found;
      status.value = found.length ? 'ready' : 'empty';
    } catch (error) {
      if (controller !== current) return;
      results.value = [];
      errorMessage.value = error.message;
      status.value = 'error';
    }
  }

  watch(query, (value) => {
    cancelPending();
    const term = value.trim();
    if (term.length < minLength) {
      results.value = [];
      status.value = 'idle';
      return;
    }
    status.value = 'loading';
    timer = setTimeout(() => run(term), debounceMs);
  });

  onScopeDispose(cancelPending);

  return { query, results, status, errorMessage };
}
