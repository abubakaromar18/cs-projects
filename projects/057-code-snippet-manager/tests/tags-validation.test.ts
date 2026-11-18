import { describe, expect, it } from "vitest";
import { countTags, normalizeTag, normalizeTags } from "@/lib/tags";
import { LIMITS, validateSnippet } from "@/lib/validation";
import { SEED_SNIPPETS } from "@/lib/seed";

describe("tags", () => {
  it("normalises case, whitespace and stray characters", () => {
    expect(normalizeTag("  Data Structures ")).toBe("data-structures");
    expect(normalizeTag("C++")).toBe("c++");
    expect(normalizeTag("Node.js!")).toBe("node.js");
    expect(normalizeTag("--a--b--")).toBe("a-b");
  });
  it("dedupes and drops empties, preserving order", () => {
    expect(normalizeTags(["Git", "cli", "git", "  ", "!!"])).toEqual(["git", "cli"]);
  });
  it("counts tags, most common first then alphabetical", () => {
    const counts = countTags(SEED_SNIPPETS);
    expect(counts.every((c, i) => i === 0 || counts[i - 1].count >= c.count)).toBe(true);
    expect(counts.find((c) => c.tag === "git")?.count).toBe(1);
  });
});

describe("validateSnippet", () => {
  const good = { title: " Hello ", language: "python", code: "print(1)\n\n", tags: "A, b, a" };

  it("accepts and cleans valid input", () => {
    const r = validateSnippet(good);
    expect(r).toEqual({
      ok: true,
      value: { title: "Hello", description: "", language: "python", code: "print(1)", tags: ["a", "b"] },
    });
  });

  it("defaults language to text", () => {
    const r = validateSnippet({ title: "x", code: "y" });
    expect(r.ok && r.value.language).toBe("text");
  });

  it("collects every error at once", () => {
    const r = validateSnippet({ title: "", code: "  ", language: "cobol", tags: [1] });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(Object.keys(r.errors).sort()).toEqual(["code", "language", "tags", "title"]);
  });

  it("enforces length limits", () => {
    const r = validateSnippet({ ...good, title: "x".repeat(LIMITS.title + 1), code: "y".repeat(LIMITS.code + 1) });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(Object.keys(r.errors).sort()).toEqual(["code", "title"]);
  });

  it("limits the number of tags", () => {
    const tags = Array.from({ length: LIMITS.tags + 1 }, (_, i) => `t${i}`);
    expect(validateSnippet({ ...good, tags }).ok).toBe(false);
  });

  it("rejects non-object bodies", () => {
    expect(validateSnippet(null).ok).toBe(false);
    expect(validateSnippet("hi").ok).toBe(false);
  });
});
