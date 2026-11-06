/**
 * A tiny time-to-live (TTL) cache.
 *
 * Weather data changes slowly relative to how often a user may refresh, so
 * caching responses for a few minutes saves battery, bandwidth and API quota.
 * The clock is injectable so tests can control time deterministically.
 */
export class TTLCache<V> {
  private store = new Map<string, { value: V; expiresAt: number }>();

  constructor(
    private readonly ttlMs: number,
    private readonly maxEntries = 50,
    private readonly now: () => number = Date.now,
  ) {}

  get(key: string): V | undefined {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (this.now() >= entry.expiresAt) {
      this.store.delete(key);
      return undefined;
    }
    // Re-insert to mark as most recently used (Map preserves insertion order).
    this.store.delete(key);
    this.store.set(key, entry);
    return entry.value;
  }

  set(key: string, value: V): void {
    this.store.delete(key);
    this.store.set(key, { value, expiresAt: this.now() + this.ttlMs });
    // Evict least-recently-used entries beyond capacity.
    while (this.store.size > this.maxEntries) {
      const oldest = this.store.keys().next().value as string;
      this.store.delete(oldest);
    }
  }

  clear(): void {
    this.store.clear();
  }

  get size(): number {
    return this.store.size;
  }
}
