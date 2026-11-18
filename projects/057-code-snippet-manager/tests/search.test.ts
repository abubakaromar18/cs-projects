import { describe, expect, it } from "vitest";
import { buildIndex, expandPrefix, search, tokenize } from "@/lib/search";
import type { Snippet } from "@/lib/types";

let n = 0;
function snip(p: Partial<Snippet>): Snippet {
  n++;
  return {
    id: p.id ?? `s${n}`,
    title: "",
    description: "",
    language: "text",
    code: "",
    tags: [],
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: `2026-01-${String(n).padStart(2, "0")}T00:00:00Z`,
    ...p,
  };
}

const data = [
  snip({ id: "debounce", title: "Debounce", tags: ["timing"], code: "function useDebounce() {}", language: "javascript" }),
  snip({ id: "throttle", title: "Throttle", description: "like debounce but periodic", tags: ["timing"], language: "javascript" }),
  snip({ id: "lru", title: "LRU cache", tags: ["cache", "data-structures"], code: "class LRUCache: pass", language: "python" }),
  snip({ id: "git", title: "Delete merged branches", tags: ["git", "cli"], code: "git branch -d", language: "bash" }),
];

describe("tokenize", () => {
  it("lowercases and splits on non-alphanumerics", () => {
    expect(tokenize("Hello, World! 42")).toEqual(["hello", "world", "42"]);
  });
  it("also splits camelCase, PascalCase and acronyms", () => {
    expect(tokenize("useDebounce")).toEqual(["usedebounce", "use", "debounce"]);
    expect(tokenize("LRUCache")).toEqual(["lrucache", "lru", "cache"]);
  });
  it("splits snake_case via the underscore", () => {
    expect(tokenize("move_to_end")).toEqual(["move", "to", "end"]);
  });
});

describe("buildIndex / expandPrefix", () => {
  it("finds all terms with a prefix using the sorted term list", () => {
    const idx = buildIndex(data);
    expect(expandPrefix(idx, "deb")).toEqual(["debounce"]);
    expect(expandPrefix(idx, "zzz")).toEqual([]);
    expect(expandPrefix(idx, "t")).toEqual(expect.arrayContaining(["throttle", "timing"]));
  });
});

describe("search", () => {
  it("returns everything newest-first when there is no query", () => {
    expect(search(data, {}).map((s) => s.id)).toEqual(["git", "lru", "throttle", "debounce"]);
  });

  it("ranks a title match above a description match", () => {
    expect(search(data, { query: "debounce" }).map((s) => s.id)).toEqual(["debounce", "throttle"]);
  });

  it("matches the last word as a prefix (search-as-you-type)", () => {
    expect(search(data, { query: "thrott" }).map((s) => s.id)).toEqual(["throttle"]);
  });

  it("requires exact matches for earlier words", () => {
    expect(search(data, { query: "thrott cache" })).toEqual([]);
  });

  it("uses AND semantics across terms", () => {
    expect(search(data, { query: "lru cache" }).map((s) => s.id)).toEqual(["lru"]);
    expect(search(data, { query: "lru git" })).toEqual([]);
  });

  it("finds identifiers by their camelCase parts", () => {
    expect(search(data, { query: "use" }).map((s) => s.id)).toEqual(["debounce"]);
  });

  it("filters by every selected tag", () => {
    expect(search(data, { tags: ["timing"] }).map((s) => s.id)).toEqual(["throttle", "debounce"]);
    expect(search(data, { tags: ["git", "cli"] }).map((s) => s.id)).toEqual(["git"]);
    expect(search(data, { tags: ["git", "timing"] })).toEqual([]);
  });

  it("filters by language and combines with the query", () => {
    expect(search(data, { language: "python" }).map((s) => s.id)).toEqual(["lru"]);
    expect(search(data, { language: "bash", query: "debounce" })).toEqual([]);
  });

  it("ignores punctuation-only queries", () => {
    expect(search(data, { query: "  !!! " })).toHaveLength(4);
  });

  it("does not mutate the input array", () => {
    const copy = [...data];
    search(data, { query: "cache" });
    expect(data).toEqual(copy);
  });
});
