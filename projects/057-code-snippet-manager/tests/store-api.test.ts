import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { SnippetStore } from "@/lib/store";
import { SEED_SNIPPETS } from "@/lib/seed";

let dir: string;
let file: string;

beforeEach(async () => {
  dir = await mkdtemp(path.join(os.tmpdir(), "snippets-"));
  file = path.join(dir, "snippets.json");
});
afterEach(() => rm(dir, { recursive: true, force: true }));

const input = { title: "T", description: "", language: "text" as const, code: "c", tags: ["x"] };

describe("SnippetStore", () => {
  it("seeds the file on first read", async () => {
    const store = new SnippetStore(file);
    expect(await store.list()).toHaveLength(SEED_SNIPPETS.length);
    expect(JSON.parse(await readFile(file, "utf8"))).toHaveLength(SEED_SNIPPETS.length);
  });

  it("creates, reads, updates and deletes", async () => {
    let clock = new Date("2026-05-01T00:00:00Z");
    const store = new SnippetStore(file, () => clock);
    const created = await store.create(input);
    expect(created.createdAt).toBe("2026-05-01T00:00:00.000Z");
    expect(await store.get(created.id)).toEqual(created);

    clock = new Date("2026-05-02T00:00:00Z");
    const updated = await store.update(created.id, { ...input, title: "T2" });
    expect(updated?.title).toBe("T2");
    expect(updated?.createdAt).toBe(created.createdAt);
    expect(updated?.updatedAt).toBe("2026-05-02T00:00:00.000Z");

    expect(await store.remove(created.id)).toBe(true);
    expect(await store.get(created.id)).toBeUndefined();
    expect(await store.remove(created.id)).toBe(false);
    expect(await store.update("missing", input)).toBeUndefined();
  });

  it("persists across store instances", async () => {
    const a = await new SnippetStore(file).create(input);
    expect(await new SnippetStore(file).get(a.id)).toEqual(a);
  });

  it("serialises concurrent writes so none are lost", async () => {
    const store = new SnippetStore(file);
    await Promise.all(Array.from({ length: 25 }, (_, i) => store.create({ ...input, title: `n${i}` })));
    expect(await store.list()).toHaveLength(SEED_SNIPPETS.length + 25);
  });

  it("leaves no temp files behind", async () => {
    const store = new SnippetStore(file);
    await store.create(input);
    expect(await readdir(dir)).toEqual(["snippets.json"]);
  });
});

describe("API route handlers", () => {
  beforeEach(() => {
    process.env.SNIPPETS_FILE = file;
  });

  it("supports the full CRUD flow over HTTP-shaped requests", async () => {
    // Import after setting SNIPPETS_FILE; reset modules so getStore() picks it up.
    vi.resetModules();
    const list = await import("@/app/api/snippets/route");
    const one = await import("@/app/api/snippets/[id]/route");
    const base = "http://localhost/api/snippets";
    const json = (body: unknown, method = "POST") =>
      new Request(base, { method, body: JSON.stringify(body), headers: { "content-type": "application/json" } });

    const bad = await list.POST(json({ title: "" }));
    expect(bad.status).toBe(400);
    expect((await bad.json()).errors.title).toBeDefined();

    const res = await list.POST(json({ title: "Quick sort", language: "python", code: "def qs(xs): ...", tags: ["sorting"] }));
    expect(res.status).toBe(201);
    const created = await res.json();

    const found = await (await list.GET(new Request(`${base}?q=quick&tag=sorting`))).json();
    expect(found.map((s: { id: string }) => s.id)).toEqual([created.id]);

    const ctx = { params: Promise.resolve({ id: created.id }) };
    expect((await one.GET(new Request(base), ctx)).status).toBe(200);

    const put = await one.PUT(json({ ...created, title: "Quicksort" }, "PUT"), ctx);
    expect((await put.json()).title).toBe("Quicksort");

    expect((await one.DELETE(new Request(base), ctx)).status).toBe(204);
    expect((await one.GET(new Request(base), ctx)).status).toBe(404);
    expect((await list.POST(new Request(base, { method: "POST", body: "not json" }))).status).toBe(400);
  });
});
