/**
 * Pure presentation helpers for the browser client. No DOM access here, so
 * everything in this file is unit-tested under Node.
 */
import type { CheckResult, Health, ServiceStatus } from "../shared/types.js";

/** "just now", "42s ago", "5m ago", "3h ago", "2d ago". */
export function relativeTime(then: number, now: number): string {
  if (then <= 0) return "never";
  const s = Math.max(0, Math.round((now - then) / 1000));
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function formatLatency(ms: number | undefined): string {
  if (ms === undefined) return "–";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(ms < 10000 ? 2 : 1)} s`;
}

export function formatUptime(pct: number | null): string {
  if (pct === null) return "–";
  return Number.isInteger(pct) ? `${pct}%` : `${pct.toFixed(1)}%`;
}

export const HEALTH_LABEL: Record<Health, string> = {
  up: "Up",
  degraded: "Slow",
  down: "Down",
  unknown: "Unchecked",
};

/** Group services by `group`, preserving the order they appear in the config. */
export function groupServices(services: readonly ServiceStatus[]): Map<string, ServiceStatus[]> {
  const groups = new Map<string, ServiceStatus[]>();
  for (const s of services) {
    const list = groups.get(s.group);
    if (list) list.push(s);
    else groups.set(s.group, [s]);
  }
  return groups;
}

/** Case-insensitive match on name, group, description and URL; every word must match. */
export function matchesFilter(s: ServiceStatus, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const haystack = `${s.name} ${s.group} ${s.description ?? ""} ${s.url}`.toLowerCase();
  return words.every((w) => haystack.includes(w));
}

/**
 * Only allow links with web-ish schemes. The config is trusted, but this keeps
 * a typo like "javascript:..." from ever becoming a clickable link.
 */
export function safeHref(url: string): string | undefined {
  try {
    const u = new URL(url);
    return ["http:", "https:", "ssh:", "smb:", "ftp:", "sftp:", "vnc:", "rdp:"].includes(u.protocol) ? u.href : undefined;
  } catch {
    return undefined;
  }
}

/** Overall banner state: the worst health among checked services. */
export function overallHealth(summary: Record<Health, number>): Health {
  if (summary.down > 0) return "down";
  if (summary.degraded > 0) return "degraded";
  if (summary.up > 0) return "up";
  return "unknown";
}

export interface SparkBar {
  x: number;
  height: number;
  health: Health;
}

/**
 * Lay out a latency sparkline as bars in a `width × height` box. Down samples
 * get a full-height bar so outages stand out; latency is scaled to the max.
 * The newest sample is always drawn at the right edge.
 */
export function sparkline(history: readonly CheckResult[], slots: number, height: number): SparkBar[] {
  const recent = history.slice(-slots);
  const maxLatency = Math.max(1, ...recent.map((r) => r.latencyMs ?? 0));
  const offset = slots - recent.length;
  return recent.map((r, i) => ({
    x: offset + i,
    health: r.health,
    height:
      r.health === "down" ? height
      : r.latencyMs === undefined ? 1
      : Math.max(2, Math.round((r.latencyMs / maxLatency) * height)),
  }));
}
