/**
 * Types shared by the server and the browser client.
 *
 * The server owns the configuration and the monitoring state; the client only
 * ever sees the `StatusSnapshot` it fetches from `/api/status`. Keeping this
 * contract in one file means a change to the wire format is a compile error
 * on both sides instead of a silent runtime bug.
 */

/** How a service is health-checked. */
export type CheckSpec =
  | {
      type: "http";
      /** Override the URL to probe (defaults to the service's `url` + `path`). */
      target?: string;
      /** Path appended to the service URL, e.g. "/health". */
      path?: string;
      /** Status codes treated as healthy. Default: any 2xx or 3xx. */
      expectStatus?: number[];
      /** Accept self-signed TLS certificates (common in home labs). */
      insecure?: boolean;
      timeoutMs: number;
      /** Responses slower than this are reported as "degraded". */
      slowMs: number;
    }
  | { type: "tcp"; host: string; port: number; timeoutMs: number; slowMs: number }
  | { type: "none" };

export interface ServiceConfig {
  /** Stable, URL-safe id derived from group + name. */
  id: string;
  name: string;
  url: string;
  group: string;
  icon?: string;
  description?: string;
  check: CheckSpec;
}

export interface DashboardConfig {
  title: string;
  intervalSeconds: number;
  /** How many past results are kept per service for uptime / sparkline. */
  historySize: number;
  services: ServiceConfig[];
}

/** Outcome of a single probe. `unknown` = not checked yet or no check configured. */
export type Health = "up" | "degraded" | "down" | "unknown";

export interface CheckResult {
  health: Health;
  /** Round-trip time in milliseconds, when the probe got that far. */
  latencyMs?: number;
  /** Short human-readable explanation, e.g. "HTTP 200" or "ECONNREFUSED". */
  detail: string;
  /** Epoch milliseconds when the probe finished. */
  checkedAt: number;
}

export interface ServiceStatus {
  id: string;
  name: string;
  url: string;
  group: string;
  icon?: string;
  description?: string;
  checkType: CheckSpec["type"];
  current: CheckResult;
  /** Oldest → newest. Bounded by `historySize`. */
  history: CheckResult[];
  /** Percentage (0–100) of checked samples that were up or degraded; null if no samples. */
  uptimePercent: number | null;
}

export interface StatusSnapshot {
  title: string;
  generatedAt: number;
  intervalSeconds: number;
  summary: Record<Health, number>;
  services: ServiceStatus[];
}
