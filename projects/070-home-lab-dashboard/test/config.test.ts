import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { ConfigError, loadConfig, parseConfig, slugify } from "../src/server/config.js";

const minimal = (services: unknown[]) => ({ groups: [{ name: "Lab", services }] });

test("slugify makes URL-safe ids", () => {
  assert.equal(slugify("Pi-hole (DNS)"), "pi-hole-dns");
  assert.equal(slugify("  Media / Jellyfin "), "media-jellyfin");
});

test("fills defaults and infers http check for http urls", () => {
  const cfg = parseConfig(minimal([{ name: "Grafana", url: "http://10.0.0.5:3000" }]));
  assert.equal(cfg.title, "Home Lab");
  assert.equal(cfg.intervalSeconds, 30);
  assert.equal(cfg.historySize, 60);
  assert.equal(cfg.services[0].id, "lab-grafana");
  assert.equal(cfg.services[0].check.type, "http");
});

test("non-http urls default to no check", () => {
  const cfg = parseConfig(minimal([{ name: "NAS", url: "smb://nas.local" }]));
  assert.deepEqual(cfg.services[0].check, { type: "none" });
});

test("tcp check takes host/port from the url when omitted", () => {
  const cfg = parseConfig(minimal([{ name: "SSH", url: "ssh://box.lan:22", check: { type: "tcp" } }]));
  const c = cfg.services[0].check;
  assert.equal(c.type, "tcp");
  if (c.type === "tcp") {
    assert.equal(c.host, "box.lan");
    assert.equal(c.port, 22);
  }
});

test("duplicate names get unique ids", () => {
  const cfg = parseConfig(minimal([
    { name: "Node", url: "http://a" }, { name: "Node", url: "http://b" },
  ]));
  assert.deepEqual(cfg.services.map((s) => s.id), ["lab-node", "lab-node-2"]);
});

test("collects every error with its path", () => {
  try {
    parseConfig({
      intervalSeconds: -1,
      groups: [{ name: "G", services: [
        { name: "", url: "not a url" },
        { name: "X", url: "http://x", check: { type: "ping" } },
        { name: "Y", url: "http://y", check: { type: "http", expectStatus: [99] } },
        { name: "Z", url: "smb://z", check: { type: "tcp" } },
      ] }],
    });
    assert.fail("expected ConfigError");
  } catch (err) {
    assert.ok(err instanceof ConfigError);
    const joined = err.errors.join("\n");
    assert.match(joined, /intervalSeconds/);
    assert.match(joined, /services\[0\]\.name/);
    assert.match(joined, /services\[0\]\.url: "not a url"/);
    assert.match(joined, /services\[1\]\.check\.type/);
    assert.match(joined, /services\[2\]\.check\.expectStatus/);
    assert.match(joined, /services\[3\]\.check\.port/);
  }
});

test("rejects empty groups and non-objects", () => {
  assert.throws(() => parseConfig([]), ConfigError);
  assert.throws(() => parseConfig({ groups: [] }), /groups: must be a non-empty array/);
});

test("loadConfig reports bad JSON and loads the example file", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "hld-"));
  const bad = path.join(dir, "bad.json");
  await writeFile(bad, "{ nope");
  await assert.rejects(loadConfig(bad), /not valid JSON/);
  const example = await loadConfig(path.resolve("services.example.json"));
  assert.ok(example.services.length >= 5);
});
