import path from "node:path";
import { describe, expect, it } from "vitest";
import { formatDate, getAllPosts, getPostBySlug, parsePost, readingTime, slugify, sortPosts } from "@/lib/posts";

const POSTS = path.join(__dirname, "..", "content", "posts");

describe("helpers", () => {
  it("slugify", () => {
    expect(slugify("My First Post!")).toBe("my-first-post");
    expect(slugify("  Café   Résumé ")).toBe("cafe-resume");
  });

  it("readingTime rounds and has a 1-minute floor", () => {
    expect(readingTime("word ".repeat(10))).toBe(1);
    expect(readingTime("word ".repeat(600))).toBe(3);
    expect(readingTime("```\n" + "x ".repeat(1000) + "\n```")).toBe(1);
  });

  it("formatDate is timezone-independent", () => {
    expect(formatDate("2026-01-01")).toBe("January 1, 2026");
  });

  it("sortPosts is newest-first and stable on ties", () => {
    const mk = (title: string, date: string) => ({ slug: title, title, date, summary: "", tags: [], readingMinutes: 1 });
    expect(sortPosts([mk("b", "2026-01-01"), mk("c", "2026-02-01"), mk("a", "2026-01-01")]).map((p) => p.title)).toEqual(["c", "a", "b"]);
  });
});

describe("parsePost", () => {
  it("validates required fields", () => {
    expect(() => parsePost("x.md", "---\ndate: 2026-01-01\n---\n")).toThrow(/title/);
    expect(() => parsePost("x.md", "---\ntitle: T\ndate: Jan 1\n---\n")).toThrow(/invalid date/);
  });

  it("parses a well-formed post", () => {
    const p = parsePost("Hello There.md", "---\ntitle: T\ndate: 2026-01-01\ntags: [a]\n---\n# H");
    expect(p).toMatchObject({ slug: "hello-there", title: "T", tags: ["a"], draft: false, html: "<h1>H</h1>" });
  });
});

describe("content directory", () => {
  it("loads real posts, newest first, excluding drafts", () => {
    const posts = getAllPosts(POSTS);
    expect(posts.length).toBeGreaterThanOrEqual(3);
    expect(posts.some((p) => p.slug === "draft-upcoming")).toBe(false);
    const dates = posts.map((p) => p.date);
    expect([...dates].sort().reverse()).toEqual(dates);
  });

  it("looks up by slug", () => {
    expect(getPostBySlug("hello-world", POSTS)?.title).toBe("Hello, World");
    expect(getPostBySlug("nope", POSTS)).toBeUndefined();
  });

  it("returns [] for a missing directory", () => {
    expect(getAllPosts(path.join(POSTS, "does-not-exist"))).toEqual([]);
  });
});
