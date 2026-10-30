import { describe, expect, it } from "vitest";
import { parseFrontmatter, parseScalar } from "@/lib/frontmatter";

describe("parseScalar", () => {
  it("types booleans, numbers, arrays and strings", () => {
    expect(parseScalar("true")).toBe(true);
    expect(parseScalar("false")).toBe(false);
    expect(parseScalar("42")).toBe(42);
    expect(parseScalar("-1.5")).toBe(-1.5);
    expect(parseScalar("[a, 'b', \"c d\"]")).toEqual(["a", "b", "c d"]);
    expect(parseScalar("[]")).toEqual([]);
    expect(parseScalar("2026-01-15")).toBe("2026-01-15");
    expect(parseScalar('"quoted: value"')).toBe("quoted: value");
  });
});

describe("parseFrontmatter", () => {
  it("splits data from content", () => {
    const doc = parseFrontmatter("---\ntitle: Hi: there\ndraft: true\n# comment\n---\n\nBody text");
    expect(doc.data).toEqual({ title: "Hi: there", draft: true });
    expect(doc.content).toBe("Body text");
  });

  it("returns the whole source when there is no front matter", () => {
    expect(parseFrontmatter("# Just markdown")).toEqual({ data: {}, content: "# Just markdown" });
  });

  it("handles CRLF line endings", () => {
    expect(parseFrontmatter("---\r\ntitle: x\r\n---\r\nbody").data.title).toBe("x");
  });

  it("rejects unterminated or malformed blocks", () => {
    expect(() => parseFrontmatter("---\ntitle: x\nbody")).toThrow(/Unterminated/);
    expect(() => parseFrontmatter("---\nnot a pair\n---\n")).toThrow(/line 2/);
  });
});
