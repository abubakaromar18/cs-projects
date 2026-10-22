/**
 * Sorting algorithms written as generator functions.
 *
 * Instead of sorting silently, each algorithm *yields* a stream of small
 * step events describing what it is doing. The visualizer replays these
 * events to animate the bars; the tests replay them to prove that the event
 * stream alone is enough to reproduce the sort.
 *
 * Every algorithm sorts a COPY of its input in ascending order and never
 * touches the caller's array.
 *
 * Event shapes:
 *   { type: 'compare',   i, j }          read a[i] and a[j] and compare them
 *   { type: 'swap',      i, j }          exchange a[i] and a[j]
 *   { type: 'overwrite', i, value }      a[i] = value (used by merge sort)
 *   { type: 'sorted',    i }             a[i] is in its final position
 *   { type: 'pivot',     i }             a[i] is the current pivot (quick sort)
 *   { type: 'range',     lo, hi }        the algorithm is working on a[lo..hi]
 */

/** @typedef {{type: string, i?: number, j?: number, value?: number, lo?: number, hi?: number}} SortEvent */

/**
 * Bubble sort: O(n²) comparisons, stable, in place.
 * Stops early when a full pass makes no swaps (best case O(n)).
 * @param {number[]} input
 * @returns {Generator<SortEvent>}
 */
export function* bubbleSort(input) {
  const a = [...input];
  const n = a.length;
  for (let end = n - 1; end > 0; end--) {
    let swapped = false;
    for (let i = 0; i < end; i++) {
      yield { type: 'compare', i, j: i + 1 };
      if (a[i] > a[i + 1]) {
        [a[i], a[i + 1]] = [a[i + 1], a[i]];
        swapped = true;
        yield { type: 'swap', i, j: i + 1 };
      }
    }
    yield { type: 'sorted', i: end };
    if (!swapped) {
      // Nothing moved, so everything before `end` is already in order.
      for (let k = end - 1; k >= 0; k--) yield { type: 'sorted', i: k };
      return;
    }
  }
  if (n > 0) yield { type: 'sorted', i: 0 };
}

/**
 * Top-down merge sort: O(n log n) always, stable, O(n) extra space.
 * Merged values are written back with 'overwrite' events.
 * @param {number[]} input
 * @returns {Generator<SortEvent>}
 */
export function* mergeSort(input) {
  const a = [...input];

  function* sort(lo, hi) {
    if (hi - lo < 1) return;
    const mid = (lo + hi) >> 1;
    yield* sort(lo, mid);
    yield* sort(mid + 1, hi);
    yield* merge(lo, mid, hi);
  }

  function* merge(lo, mid, hi) {
    yield { type: 'range', lo, hi };
    const left = a.slice(lo, mid + 1);
    const right = a.slice(mid + 1, hi + 1);
    let i = 0;
    let j = 0;
    let k = lo;
    while (i < left.length && j < right.length) {
      // Compare the original positions the two heads came from.
      yield { type: 'compare', i: lo + i, j: mid + 1 + j };
      // `<=` keeps equal elements in their original order (stability).
      const value = left[i] <= right[j] ? left[i++] : right[j++];
      a[k] = value;
      yield { type: 'overwrite', i: k++, value };
    }
    while (i < left.length) {
      a[k] = left[i++];
      yield { type: 'overwrite', i: k, value: a[k] };
      k++;
    }
    while (j < right.length) {
      a[k] = right[j++];
      yield { type: 'overwrite', i: k, value: a[k] };
      k++;
    }
  }

  yield* sort(0, a.length - 1);
  for (let i = 0; i < a.length; i++) yield { type: 'sorted', i };
}

/**
 * Quick sort with Lomuto partitioning and a median-of-three pivot.
 * O(n log n) expected, O(n²) worst case, not stable, in place.
 * Recurses into the smaller side first so stack depth stays O(log n).
 * @param {number[]} input
 * @returns {Generator<SortEvent>}
 */
export function* quickSort(input) {
  const a = [...input];

  function* swap(i, j) {
    if (i === j) return;
    [a[i], a[j]] = [a[j], a[i]];
    yield { type: 'swap', i, j };
  }

  /** Move the median of a[lo], a[mid], a[hi] to a[hi] to use as pivot. */
  function* choosePivot(lo, hi) {
    const mid = (lo + hi) >> 1;
    yield { type: 'compare', i: lo, j: mid };
    if (a[mid] < a[lo]) yield* swap(lo, mid);
    yield { type: 'compare', i: lo, j: hi };
    if (a[hi] < a[lo]) yield* swap(lo, hi);
    yield { type: 'compare', i: mid, j: hi };
    if (a[mid] < a[hi]) yield* swap(mid, hi);
    // Now a[lo] <= a[hi] <= a[mid]: a[hi] is the median.
  }

  function* partition(lo, hi) {
    yield* choosePivot(lo, hi);
    yield { type: 'pivot', i: hi };
    const pivot = a[hi];
    let store = lo;
    for (let i = lo; i < hi; i++) {
      yield { type: 'compare', i, j: hi };
      if (a[i] < pivot) {
        yield* swap(i, store);
        store++;
      }
    }
    yield* swap(store, hi);
    return store;
  }

  function* sort(lo, hi) {
    while (lo < hi) {
      yield { type: 'range', lo, hi };
      const p = yield* partition(lo, hi);
      yield { type: 'sorted', i: p };
      // Recurse on the smaller half, loop on the larger one.
      if (p - lo < hi - p) {
        yield* sort(lo, p - 1);
        lo = p + 1;
      } else {
        yield* sort(p + 1, hi);
        hi = p - 1;
      }
    }
    if (lo === hi) yield { type: 'sorted', i: lo };
  }

  yield* sort(0, a.length - 1);
}

/**
 * Heap sort: build a max-heap in place, then repeatedly move the max to
 * the end. O(n log n) always, O(1) extra space, not stable.
 * @param {number[]} input
 * @returns {Generator<SortEvent>}
 */
export function* heapSort(input) {
  const a = [...input];
  const n = a.length;

  /** Push a[root] down until the subtree a[root..size) is a max-heap. */
  function* siftDown(root, size) {
    for (;;) {
      const left = 2 * root + 1;
      const right = left + 1;
      let largest = root;
      if (left < size) {
        yield { type: 'compare', i: left, j: largest };
        if (a[left] > a[largest]) largest = left;
      }
      if (right < size) {
        yield { type: 'compare', i: right, j: largest };
        if (a[right] > a[largest]) largest = right;
      }
      if (largest === root) return;
      [a[root], a[largest]] = [a[largest], a[root]];
      yield { type: 'swap', i: root, j: largest };
      root = largest;
    }
  }

  // Heapify: sift down every internal node, bottom-up. O(n) total.
  for (let i = (n >> 1) - 1; i >= 0; i--) yield* siftDown(i, n);

  for (let end = n - 1; end > 0; end--) {
    [a[0], a[end]] = [a[end], a[0]];
    yield { type: 'swap', i: 0, j: end };
    yield { type: 'sorted', i: end };
    yield* siftDown(0, end);
  }
  if (n > 0) yield { type: 'sorted', i: 0 };
}

/** Registry used by the UI and tests, with complexity metadata for display. */
export const ALGORITHMS = {
  bubble: {
    name: 'Bubble sort', fn: bubbleSort,
    best: 'O(n)', average: 'O(n²)', worst: 'O(n²)', space: 'O(1)', stable: true,
  },
  merge: {
    name: 'Merge sort', fn: mergeSort,
    best: 'O(n log n)', average: 'O(n log n)', worst: 'O(n log n)', space: 'O(n)', stable: true,
  },
  quick: {
    name: 'Quick sort', fn: quickSort,
    best: 'O(n log n)', average: 'O(n log n)', worst: 'O(n²)', space: 'O(log n)', stable: false,
  },
  heap: {
    name: 'Heap sort', fn: heapSort,
    best: 'O(n log n)', average: 'O(n log n)', worst: 'O(n log n)', space: 'O(1)', stable: false,
  },
};
