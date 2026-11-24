/**
 * Health-check probes.
 *
 * Each probe resolves (never rejects) to a `CheckResult`, so the monitor can
 * run many of them with `Promise.all` without one failure poisoning the rest.
 * Every probe has a hard timeout: a hung service must not hang the dashboard.
 */
import http from "node:http";
import https from "node:https";
import net from "node:net";
import type { CheckResult, CheckSpec, Health, ServiceConfig } from "../shared/types.js";

/** Monotonic clock, so latency is immune to wall-clock adjustments (NTP, DST). */
const now = (): number => performance.now();

/** Classify a successful probe as up or degraded based on latency. */
export function classifyLatency(latencyMs: number, slowMs: number): Health {
  return latencyMs > slowMs ? "degraded" : "up";
}

/** Default "healthy" status codes: anything 2xx or 3xx. */
export function isExpectedStatus(status: number, expect?: number[]): boolean {
  return expect ? expect.includes(status) : status >= 200 && status < 400;
}

/** Build the URL an HTTP check probes: `target` wins, otherwise service url + path. */
export function httpTarget(service: ServiceConfig, spec: Extract<CheckSpec, { type: "http" }>): URL {
  if (spec.target) return new URL(spec.target);
  const url = new URL(service.url);
  if (spec.path) {
    // Join paths without doubling or dropping the slash.
    url.pathname = url.pathname.replace(/\/+$/, "") + "/" + spec.path.replace(/^\/+/, "");
  }
  return url;
}

/**
 * HTTP(S) GET probe. Redirects are not followed: a 302 to a login page still
 * proves the service is answering, which is what a status light should show.
 */
export function checkHttp(url: URL, spec: Extract<CheckSpec, { type: "http" }>): Promise<CheckResult> {
  return new Promise((resolve) => {
    const start = now();
    const lib = url.protocol === "https:" ? https : http;
    let settled = false;
    const finish = (result: Omit<CheckResult, "checkedAt">) => {
      if (settled) return;
      settled = true;
      resolve({ ...result, checkedAt: Date.now() });
    };

    const req = lib.request(
      url,
      {
        method: "GET",
        headers: { "user-agent": "homelab-dashboard/1.0", accept: "*/*" },
        // Only relaxes verification when the user opted in for this service.
        rejectUnauthorized: !spec.insecure,
        timeout: spec.timeoutMs,
      },
      (res) => {
        const latencyMs = Math.round(now() - start);
        const status = res.statusCode ?? 0;
        res.resume(); // drain and discard the body so the socket is released
        if (isExpectedStatus(status, spec.expectStatus)) {
          finish({ health: classifyLatency(latencyMs, spec.slowMs), latencyMs, detail: `HTTP ${status}` });
        } else {
          finish({ health: "down", latencyMs, detail: `HTTP ${status} (unexpected)` });
        }
      },
    );
    req.on("timeout", () => {
      req.destroy();
      finish({ health: "down", detail: `timed out after ${spec.timeoutMs} ms` });
    });
    req.on("error", (err: NodeJS.ErrnoException) => finish({ health: "down", detail: describeError(err) }));
    req.end();
  });
}

/** TCP connect probe: healthy if the port accepts a connection. */
export function checkTcp(spec: Extract<CheckSpec, { type: "tcp" }>): Promise<CheckResult> {
  return new Promise((resolve) => {
    const start = now();
    const socket = net.createConnection({ host: spec.host, port: spec.port });
    let settled = false;
    const finish = (result: Omit<CheckResult, "checkedAt">) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve({ ...result, checkedAt: Date.now() });
    };
    socket.setTimeout(spec.timeoutMs);
    socket.once("connect", () => {
      const latencyMs = Math.round(now() - start);
      finish({ health: classifyLatency(latencyMs, spec.slowMs), latencyMs, detail: `port ${spec.port} open` });
    });
    socket.once("timeout", () => finish({ health: "down", detail: `timed out after ${spec.timeoutMs} ms` }));
    socket.once("error", (err: NodeJS.ErrnoException) => finish({ health: "down", detail: describeError(err) }));
  });
}

/** Run whichever probe the service is configured for. */
export function runCheck(service: ServiceConfig): Promise<CheckResult> {
  const spec = service.check;
  switch (spec.type) {
    case "http":
      return checkHttp(httpTarget(service, spec), spec);
    case "tcp":
      return checkTcp(spec);
    case "none":
      return Promise.resolve({ health: "unknown", detail: "no health check", checkedAt: Date.now() });
  }
}

/** Map common socket errors to friendlier text for the dashboard. */
export function describeError(err: NodeJS.ErrnoException): string {
  switch (err.code) {
    case "ECONNREFUSED": return "connection refused";
    case "ENOTFOUND":
    case "EAI_AGAIN": return "host not found";
    case "EHOSTUNREACH":
    case "ENETUNREACH": return "host unreachable";
    case "ECONNRESET": return "connection reset";
    case "DEPTH_ZERO_SELF_SIGNED_CERT":
    case "SELF_SIGNED_CERT_IN_CHAIN": return "self-signed certificate (set insecure: true)";
    case "CERT_HAS_EXPIRED": return "TLS certificate expired";
    default: return err.code ? `${err.code}: ${err.message}` : err.message;
  }
}
