import { test, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import net from "node:net";
import type { AddressInfo } from "node:net";
import {
  checkHttp, checkTcp, classifyLatency, describeError, httpTarget, isExpectedStatus, runCheck,
} from "../src/server/checks.js";
import type { CheckSpec, ServiceConfig } from "../src/shared/types.js";

type HttpSpec = Extract<CheckSpec, { type: "http" }>;
const spec = (over: Partial<HttpSpec> = {}): HttpSpec => ({ type: "http", timeoutMs: 1000, slowMs: 500, ...over });

// A local test server: /ok → 200, /redirect → 302, /broken → 500, /slow → waits.
const server = http.createServer((req, res) => {
  if (req.url === "/ok") res.end("ok");
  else if (req.url === "/redirect") res.writeHead(302, { location: "/login" }).end();
  else if (req.url === "/broken") res.writeHead(500).end();
  else if (req.url === "/slow") setTimeout(() => res.end("late"), 300);
  else res.writeHead(404).end();
});
await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
after(() => server.close());

/** A port that was just free (nothing is listening on it). */
async function closedPort(): Promise<number> {
  const s = net.createServer();
  await new Promise<void>((r) => s.listen(0, "127.0.0.1", r));
  const port = (s.address() as AddressInfo).port;
  await new Promise<void>((r) => s.close(() => r()));
  return port;
}

test("status-code and latency classification", () => {
  assert.equal(isExpectedStatus(204), true);
  assert.equal(isExpectedStatus(301), true);
  assert.equal(isExpectedStatus(404), false);
  assert.equal(isExpectedStatus(401, [200, 401]), true);
  assert.equal(classifyLatency(100, 500), "up");
  assert.equal(classifyLatency(501, 500), "degraded");
});

test("httpTarget joins path or uses target", () => {
  const svc = { url: "http://h:1/app/" } as ServiceConfig;
  assert.equal(httpTarget(svc, spec({ path: "/health" })).href, "http://h:1/app/health");
  assert.equal(httpTarget(svc, spec({ target: "http://other/x" })).href, "http://other/x");
  assert.equal(httpTarget(svc, spec()).href, "http://h:1/app/");
});

test("http: 200 is up with latency", async () => {
  const r = await checkHttp(new URL(`${base}/ok`), spec());
  assert.equal(r.health, "up");
  assert.equal(r.detail, "HTTP 200");
  assert.ok(typeof r.latencyMs === "number" && r.latencyMs >= 0);
});

test("http: redirect counts as up, 500 as down, custom expectStatus respected", async () => {
  assert.equal((await checkHttp(new URL(`${base}/redirect`), spec())).health, "up");
  const broken = await checkHttp(new URL(`${base}/broken`), spec());
  assert.equal(broken.health, "down");
  assert.match(broken.detail, /500/);
  assert.equal((await checkHttp(new URL(`${base}/missing`), spec({ expectStatus: [404] }))).health, "up");
});

test("http: slow response is degraded; very slow times out", async () => {
  assert.equal((await checkHttp(new URL(`${base}/slow`), spec({ slowMs: 100 }))).health, "degraded");
  const t = await checkHttp(new URL(`${base}/slow`), spec({ timeoutMs: 50 }));
  assert.equal(t.health, "down");
  assert.match(t.detail, /timed out/);
});

test("http: refused connection is down with a friendly message", async () => {
  const r = await checkHttp(new URL(`http://127.0.0.1:${await closedPort()}/`), spec());
  assert.equal(r.health, "down");
  assert.equal(r.detail, "connection refused");
});

test("tcp: open and closed ports", async () => {
  const port = (server.address() as AddressInfo).port;
  const open = await checkTcp({ type: "tcp", host: "127.0.0.1", port, timeoutMs: 1000, slowMs: 500 });
  assert.equal(open.health, "up");
  assert.match(open.detail, /open/);
  const closed = await checkTcp({ type: "tcp", host: "127.0.0.1", port: await closedPort(), timeoutMs: 1000, slowMs: 500 });
  assert.equal(closed.health, "down");
});

test("runCheck with type none is unknown", async () => {
  const r = await runCheck({ id: "x", name: "x", url: "smb://x", group: "g", check: { type: "none" } });
  assert.equal(r.health, "unknown");
});

test("describeError maps codes", () => {
  const e = (code: string) => Object.assign(new Error("boom"), { code });
  assert.equal(describeError(e("ENOTFOUND")), "host not found");
  assert.match(describeError(e("DEPTH_ZERO_SELF_SIGNED_CERT")), /insecure/);
  assert.equal(describeError(e("EWEIRD")), "EWEIRD: boom");
});
