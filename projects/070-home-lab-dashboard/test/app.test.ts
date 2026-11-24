import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { createApp, safeJoin } from "../src/server/app.js";
import { Monitor } from "../src/server/monitor.js";
import type { StatusSnapshot } from "../src/shared/types.js";

let server: Server;
let base = "";
let checks = 0;

before(async () => {
  const publicDir = await mkdtemp(path.join(tmpdir(), "hld-pub-"));
  const clientDir = await mkdtemp(path.join(tmpdir(), "hld-cli-"));
  await writeFile(path.join(publicDir, "index.html"), "<h1>dash</h1>");
  await writeFile(path.join(clientDir, "app.js"), "console.log(1)");
  const monitor = new Monitor(
    { title: "Test Lab", intervalSeconds: 60, historySize: 5,
      services: [{ id: "g-a", name: "A", url: "http://a", group: "g", check: { type: "http", timeoutMs: 1, slowMs: 1 } }] },
    { checker: async () => { checks++; return { health: "up", latencyMs: 7, detail: "HTTP 200", checkedAt: Date.now() }; } },
  );
  server = createApp(monitor, { publicDir, clientDir });
  await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

test("safeJoin blocks traversal", () => {
  assert.equal(safeJoin("/srv/www", "/../etc/passwd"), "/srv/www/etc/passwd"); // normalised inside root
  assert.equal(safeJoin("/srv/www", "/%2e%2e/%2e%2e/etc/passwd"), "/srv/www/etc/passwd");
  assert.equal(safeJoin("/srv/www", "/a%00b"), undefined);
  assert.equal(safeJoin("/srv/www", "/%E0%A4%A"), undefined);
  assert.equal(safeJoin("/srv/www", "/css/site.css"), "/srv/www/css/site.css");
});

test("serves index and client JS with correct types", async () => {
  const index = await fetch(`${base}/`);
  assert.equal(index.status, 200);
  assert.match(index.headers.get("content-type") ?? "", /text\/html/);
  assert.equal(await index.text(), "<h1>dash</h1>");
  const js = await fetch(`${base}/app.js`);
  assert.match(js.headers.get("content-type") ?? "", /javascript/);
  assert.equal((await fetch(`${base}/nope.txt`)).status, 404);
});

test("status before and after refresh", async () => {
  const before = (await (await fetch(`${base}/api/status`)).json()) as StatusSnapshot;
  assert.equal(before.title, "Test Lab");
  assert.equal(before.summary.unknown, 1);

  assert.equal((await fetch(`${base}/api/refresh`)).status, 405);
  const res = await fetch(`${base}/api/refresh`, { method: "POST" });
  const after = (await res.json()) as StatusSnapshot;
  assert.equal(after.services[0].current.health, "up");
  assert.equal(after.services[0].current.latencyMs, 7);
  assert.equal(after.services[0].uptimePercent, 100);
  assert.equal(checks, 1);
});

test("health and unknown api routes", async () => {
  const h = (await (await fetch(`${base}/api/health`)).json()) as { ok: boolean };
  assert.equal(h.ok, true);
  assert.equal((await fetch(`${base}/api/nope`)).status, 404);
  assert.equal((await fetch(`${base}/api/status`, { method: "DELETE" })).status, 405);
});
