/**
 * Sliding-window rate limiter.
 *
 * For each key (e.g. client IP) we keep the timestamps of recent hits. A hit is
 * allowed if fewer than `limit` hits occurred in the last `windowMs`.
 * Memory per key is O(limit), because older timestamps are pruned on each call.
 *
 * In-memory state is per server instance — fine for a personal site on one
 * node; a multi-instance deploy would back this with Redis or similar.
 */

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  /** Milliseconds until the next hit would be allowed (0 if allowed now). */
  retryAfterMs: number;
}

export class SlidingWindowRateLimiter {
  private readonly hits = new Map<string, number[]>();

  constructor(
    private readonly limit: number,
    private readonly windowMs: number,
    private readonly now: () => number = Date.now,
  ) {
    if (limit < 1 || windowMs <= 0) throw new Error("limit must be >= 1 and windowMs > 0");
  }

  check(key: string): RateLimitResult {
    const t = this.now();
    const cutoff = t - this.windowMs;
    const recent = (this.hits.get(key) ?? []).filter((ts) => ts > cutoff);

    if (recent.length >= this.limit) {
      this.hits.set(key, recent);
      return { allowed: false, remaining: 0, retryAfterMs: recent[0] + this.windowMs - t };
    }

    recent.push(t);
    this.hits.set(key, recent);
    return { allowed: true, remaining: this.limit - recent.length, retryAfterMs: 0 };
  }

  /** Drop keys with no recent hits so the map cannot grow without bound. */
  sweep(): void {
    const cutoff = this.now() - this.windowMs;
    for (const [key, ts] of this.hits) {
      if (ts.every((x) => x <= cutoff)) this.hits.delete(key);
    }
  }

  get size(): number {
    return this.hits.size;
  }
}
