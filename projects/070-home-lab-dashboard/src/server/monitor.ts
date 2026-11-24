/**
 * The monitor polls every service on an interval and keeps a bounded history.
 *
 * Design notes:
 * - History is a fixed-capacity ring buffer, so memory use is O(services × historySize)
 *   no matter how long the dashboard runs.
 * - Probes run concurrently, with a cap, so 40 services with 5 s timeouts
 *   still finish a round in seconds rather than minutes.
 * - Rounds never overlap: if a round is still running when the timer fires,
 *   that tick is skipped instead of piling up requests.
 * - The checker is injected, so tests can drive the monitor deterministically.
 */
import { runCheck } from "./checks.js";
import type {
  CheckResult, DashboardConfig, Health, ServiceConfig, ServiceStatus, StatusSnapshot,
} from "../shared/types.js";

/** Fixed-capacity FIFO: pushing onto a full buffer overwrites the oldest item. */
export class RingBuffer<T> {
  private readonly items: (T | undefined)[];
  private start = 0;
  private count = 0;

  constructor(public readonly capacity: number) {
    if (!Number.isInteger(capacity) || capacity < 1) throw new RangeError("capacity must be a positive integer");
    this.items = new Array<T | undefined>(capacity);
  }

  get size(): number {
    return this.count;
  }

  push(item: T): void {
    const end = (this.start + this.count) % this.capacity;
    this.items[end] = item;
    if (this.count < this.capacity) this.count++;
    else this.start = (this.start + 1) % this.capacity; // overwrote the oldest
  }

  /** Items oldest → newest. */
  toArray(): T[] {
    const out: T[] = [];
    for (let i = 0; i < this.count; i++) out.push(this.items[(this.start + i) % this.capacity] as T);
    return out;
  }

  last(): T | undefined {
    return this.count === 0 ? undefined : this.items[(this.start + this.count - 1) % this.capacity];
  }
}

/** Uptime over the samples that were actually checked ("unknown" is ignored). */
export function uptimePercent(history: readonly CheckResult[]): number | null {
  const checked = history.filter((r) => r.health !== "unknown");
  if (checked.length === 0) return null;
  const ok = checked.filter((r) => r.health === "up" || r.health === "degraded").length;
  return Math.round((ok / checked.length) * 1000) / 10; // one decimal place
}

/** Run async tasks with at most `limit` in flight; results keep input order. */
export async function mapWithConcurrency<T, R>(
  items: readonly T[], limit: number, fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++; // safe: JS is single-threaded between awaits
      results[i] = await fn(items[i]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

export type Checker = (service: ServiceConfig) => Promise<CheckResult>;

export interface MonitorOptions {
  checker?: Checker;
  concurrency?: number;
  clock?: () => number;
}

export class Monitor {
  private readonly history = new Map<string, RingBuffer<CheckResult>>();
  private readonly checker: Checker;
  private readonly concurrency: number;
  private readonly clock: () => number;
  private timer: NodeJS.Timeout | undefined;
  private running: Promise<void> | undefined;
  private rounds = 0;

  constructor(private readonly config: DashboardConfig, options: MonitorOptions = {}) {
    this.checker = options.checker ?? runCheck;
    this.concurrency = options.concurrency ?? 8;
    this.clock = options.clock ?? Date.now;
    for (const s of config.services) this.history.set(s.id, new RingBuffer(config.historySize));
  }

  /** Number of completed rounds (handy for tests and logs). */
  get completedRounds(): number {
    return this.rounds;
  }

  /**
   * Check every service once. Concurrent callers share the in-flight round
   * rather than starting a second one.
   */
  checkAll(): Promise<void> {
    if (this.running) return this.running;
    this.running = (async () => {
      try {
        const results = await mapWithConcurrency(this.config.services, this.concurrency, async (s) => {
          try {
            return await this.checker(s);
          } catch (err) {
            // A buggy checker must not take down the whole round.
            return { health: "down", detail: `check failed: ${(err as Error).message}`, checkedAt: this.clock() } satisfies CheckResult;
          }
        });
        this.config.services.forEach((s, i) => this.history.get(s.id)!.push(results[i]));
        this.rounds++;
      } finally {
        this.running = undefined;
      }
    })();
    return this.running;
  }

  /** Start periodic polling. The first round runs immediately. */
  start(): void {
    if (this.timer) return;
    void this.checkAll();
    this.timer = setInterval(() => {
      if (!this.running) void this.checkAll(); // skip the tick if the last round is still going
    }, this.config.intervalSeconds * 1000);
    this.timer.unref?.(); // don't keep the process alive just for the timer
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }

  /** Build the JSON snapshot the dashboard renders. */
  snapshot(): StatusSnapshot {
    const summary: Record<Health, number> = { up: 0, degraded: 0, down: 0, unknown: 0 };
    const services: ServiceStatus[] = this.config.services.map((s) => {
      const buf = this.history.get(s.id)!;
      const history = buf.toArray();
      const current: CheckResult = buf.last() ?? { health: "unknown", detail: "not checked yet", checkedAt: 0 };
      summary[current.health]++;
      return {
        id: s.id, name: s.name, url: s.url, group: s.group, icon: s.icon, description: s.description,
        checkType: s.check.type, current, history, uptimePercent: uptimePercent(history),
      };
    });
    return {
      title: this.config.title,
      generatedAt: this.clock(),
      intervalSeconds: this.config.intervalSeconds,
      summary,
      services,
    };
  }
}
