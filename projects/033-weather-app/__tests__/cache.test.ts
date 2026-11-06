import { TTLCache } from '../src/api/cache';

describe('TTLCache', () => {
  it('returns values until they expire', () => {
    let now = 1000;
    const cache = new TTLCache<string>(500, 10, () => now);
    cache.set('a', 'x');
    now = 1499;
    expect(cache.get('a')).toBe('x');
    now = 1500;
    expect(cache.get('a')).toBeUndefined();
    expect(cache.size).toBe(0);
  });

  it('evicts the least recently used entry when full', () => {
    const cache = new TTLCache<number>(10_000, 2, () => 0);
    cache.set('a', 1);
    cache.set('b', 2);
    cache.get('a'); // touch "a" so "b" is now least recently used
    cache.set('c', 3);
    expect(cache.get('a')).toBe(1);
    expect(cache.get('b')).toBeUndefined();
    expect(cache.get('c')).toBe(3);
  });
});
