import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { AddressInfo } from "node:net";
import { chartGeometry, fmtDuration, modeId } from "../src/web/format.js";
import { makeServer, safeResolve } from "../src/server/serve.js";

test("fmtDuration", () => {
  assert.equal(fmtDuration(7_500), "7.5s");
  assert.equal(fmtDuration(65_000), "1:05");
});

test("modeId encodes options", () => {
  assert.equal(modeId("words", 25, false, false), "words-25");
  assert.equal(modeId("time", 30, true, true), "time-30+punct+num");
});

test("chartGeometry scales points into the box", () => {
  const g = chartGeometry(
    [{ second: 1, wpm: 50, burstWpm: 100, errors: 0 }, { second: 2, wpm: 60, burstWpm: 40, errors: 2 }],
    200, 100,
  );
  assert.ok(Math.abs(g.maxWpm - 110) < 1e-9);
  assert.match(g.wpmPath, /^M100,54\.5 L200,45\.5$/);
  assert.equal(g.errorDots.length, 1);
  assert.equal(g.errorDots[0]!.x, 200);
  assert.deepEqual(chartGeometry([], 10, 10).wpmPath, "");
});

test("safeResolve blocks traversal", () => {
  assert.equal(safeResolve("/srv/pub", "/a/b.js"), "/srv/pub/a/b.js");
  assert.equal(safeResolve("/srv/pub", "/../etc/passwd"), "/srv/pub/etc/passwd");
  assert.equal(safeResolve("/srv/pub", "/%2e%2e/%2e%2e/etc/passwd"), "/srv/pub/etc/passwd");
  assert.equal(safeResolve("/srv/pub", "/%E0%A4%A"), null);
  assert.equal(safeResolve("/srv/pub", "/a%00b"), null);
});

test("static server serves public and dist, 404s and 405s", async () => {
  const root = await mkdtemp(join(tmpdir(), "tst-"));
  await mkdir(join(root, "public"));
  await mkdir(join(root, "dist", "web"), { recursive: true });
  await writeFile(join(root, "public", "index.html"), "<h1>hi</h1>");
  await writeFile(join(root, "dist", "web", "app.js"), "export {}");
  const srv = makeServer({ publicDir: join(root, "public"), distDir: join(root, "dist") });
  await new Promise<void>((r) => srv.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${(srv.address() as AddressInfo).port}`;
  try {
    const idx = await fetch(`${base}/`);
    assert.equal(idx.status, 200);
    assert.match(idx.headers.get("content-type")!, /text\/html/);
    assert.equal(await idx.text(), "<h1>hi</h1>");
    const js = await fetch(`${base}/dist/web/app.js`);
    assert.match(js.headers.get("content-type")!, /javascript/);
    assert.equal((await fetch(`${base}/nope.css`)).status, 404);
    assert.equal((await fetch(`${base}/dist/web`)).status, 404, "directories are not served");
    assert.equal((await fetch(`${base}/`, { method: "POST" })).status, 405);
  } finally {
    srv.close();
  }
});
