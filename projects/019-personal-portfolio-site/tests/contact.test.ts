import { describe, expect, it } from "vitest";
import { handleContact } from "@/lib/contactHandler";
import { InMemoryMessageStore } from "@/lib/messageStore";
import { SlidingWindowRateLimiter } from "@/lib/rateLimit";
import { validateContact } from "@/lib/validation";

const good = { name: "Ada", email: "Ada@Example.com", message: "Hello, I like your site!" };

describe("validateContact", () => {
  it("accepts and normalises valid input", () => {
    const r = validateContact({ ...good, name: "  Ada  " });
    expect(r).toEqual({ ok: true, isSpam: false, value: { name: "Ada", email: "ada@example.com", message: good.message } });
  });

  it("reports every invalid field", () => {
    const r = validateContact({ name: "", email: "nope", message: "short" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(Object.keys(r.errors).sort()).toEqual(["email", "message", "name"]);
  });

  it("handles non-object and non-string input", () => {
    expect(validateContact(null).ok).toBe(false);
    expect(validateContact({ name: 5, email: [], message: {} }).ok).toBe(false);
  });

  it("flags the honeypot", () => {
    const r = validateContact({ ...good, website: "http://spam" });
    expect(r.ok && r.isSpam).toBe(true);
  });
});

describe("SlidingWindowRateLimiter", () => {
  it("allows up to the limit, then blocks until the window slides", () => {
    let now = 0;
    const rl = new SlidingWindowRateLimiter(2, 1000, () => now);
    expect(rl.check("ip").allowed).toBe(true);
    now = 400;
    expect(rl.check("ip")).toEqual({ allowed: true, remaining: 0, retryAfterMs: 0 });
    now = 500;
    expect(rl.check("ip")).toEqual({ allowed: false, remaining: 0, retryAfterMs: 500 });
    expect(rl.check("other").allowed).toBe(true); // keys are independent
    now = 1001; // first hit (t=0) has left the window
    expect(rl.check("ip").allowed).toBe(true);
  });

  it("sweeps idle keys", () => {
    let now = 0;
    const rl = new SlidingWindowRateLimiter(1, 100, () => now);
    rl.check("a");
    now = 50;
    rl.check("b");
    now = 120;
    rl.sweep();
    expect(rl.size).toBe(1);
  });

  it("rejects invalid configuration", () => {
    expect(() => new SlidingWindowRateLimiter(0, 10)).toThrow();
  });
});

describe("handleContact", () => {
  const deps = () => ({ limiter: new SlidingWindowRateLimiter(3, 60_000), store: new InMemoryMessageStore() });

  it("stores a valid message (201)", async () => {
    const d = deps();
    const res = await handleContact("ip", JSON.stringify(good), d);
    expect(res.status).toBe(201);
    expect(await d.store.list()).toHaveLength(1);
  });

  it("returns 400 for bad JSON and 422 for invalid fields", async () => {
    const d = deps();
    expect((await handleContact("ip", "{oops", d)).status).toBe(400);
    const res = await handleContact("ip", JSON.stringify({ ...good, email: "x" }), d);
    expect(res.status).toBe(422);
    expect(res.body.errors).toHaveProperty("email");
  });

  it("silently drops spam with a fake success", async () => {
    const d = deps();
    const res = await handleContact("ip", JSON.stringify({ ...good, website: "x" }), d);
    expect(res).toEqual({ status: 200, body: { ok: true } });
    expect(await d.store.list()).toHaveLength(0);
  });

  it("rate limits with 429 and Retry-After", async () => {
    const d = deps();
    for (let i = 0; i < 3; i++) await handleContact("ip", JSON.stringify(good), d);
    const res = await handleContact("ip", JSON.stringify(good), d);
    expect(res.status).toBe(429);
    expect(Number(res.headers?.["Retry-After"])).toBeGreaterThan(0);
  });
});
