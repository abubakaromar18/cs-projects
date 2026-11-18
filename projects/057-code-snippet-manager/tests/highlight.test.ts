import { describe, expect, it } from "vitest";
import { highlight, toLines, type Token } from "@/lib/highlight";
import { LANGUAGES } from "@/lib/types";

const kinds = (tokens: Token[], kind: string) => tokens.filter((t) => t.kind === kind).map((t) => t.text);

describe("highlight", () => {
  it("is lossless for every language", () => {
    const src = `const x = "a\\"b"; // hi\n# py\n$HOME 'q' 0x1F -- sql\n{"k": [1, true]}`;
    for (const lang of LANGUAGES) {
      expect(highlight(src, lang).map((t) => t.text).join("")).toBe(src);
    }
  });

  it("tokenises JavaScript keywords, strings, numbers, comments and calls", () => {
    const t = highlight(`const n = parseInt("42", 10); // convert`, "javascript");
    expect(kinds(t, "keyword")).toEqual(["const"]);
    expect(kinds(t, "string")).toEqual(['"42"']);
    expect(kinds(t, "number")).toEqual(["10"]);
    expect(kinds(t, "comment")).toEqual(["// convert"]);
    expect(kinds(t, "function")).toEqual(["parseInt"]);
  });

  it("does not treat comment markers inside strings as comments", () => {
    const t = highlight(`const url = "http://example.com";`, "javascript");
    expect(kinds(t, "comment")).toEqual([]);
    expect(kinds(t, "string")).toEqual(['"http://example.com"']);
  });

  it("handles template literals and block comments spanning lines", () => {
    const t = highlight("/* a\nb */ `x\n${y}`", "javascript");
    expect(kinds(t, "comment")).toEqual(["/* a\nb */"]);
    expect(kinds(t, "string")).toEqual(["`x\n${y}`"]);
  });

  it("knows TypeScript-only keywords and primitive types", () => {
    const t = highlight("interface P { name: string }", "typescript");
    expect(kinds(t, "keyword")).toContain("interface");
    expect(kinds(t, "type")).toEqual(expect.arrayContaining(["P", "string"]));
  });

  it("tokenises Python triple-quoted strings, decorators and literals", () => {
    const t = highlight(`@cache\ndef f():\n    """doc\n    string"""\n    return None  # nothing`, "python");
    expect(kinds(t, "function")).toEqual(["@cache", "f"]);
    expect(kinds(t, "string")).toEqual(['"""doc\n    string"""']);
    expect(kinds(t, "literal")).toEqual(["None"]);
    expect(kinds(t, "comment")).toEqual(["# nothing"]);
  });

  it("tokenises Rust macros and lifetimes without breaking", () => {
    const t = highlight(`fn f<'a>(s: &'a str) { println!("{}", s); }`, "rust");
    expect(kinds(t, "function")).toContain("println!");
    expect(kinds(t, "type")).toContain("str");
    expect(kinds(t, "string")).toEqual(['"{}"']);
  });

  it("tokenises bash variables and single-quoted strings", () => {
    const t = highlight(`echo "$HOME" '$literal' \${PATH}`, "bash");
    expect(kinds(t, "function")).toEqual(["echo"]);
    expect(kinds(t, "variable")).toEqual(["${PATH}"]);
    expect(kinds(t, "string")).toEqual(['"$HOME"', "'$literal'"]);
  });

  it("is case-insensitive for SQL keywords and handles doubled quotes", () => {
    const t = highlight(`select name FROM users WHERE note = 'it''s' -- c`, "sql");
    expect(kinds(t, "keyword")).toEqual(["select", "FROM", "WHERE"]);
    expect(kinds(t, "string")).toEqual(["'it''s'"]);
    expect(kinds(t, "comment")).toEqual(["-- c"]);
  });

  it("distinguishes JSON keys from string values", () => {
    const t = highlight(`{"name": "Ada", "age": -3.5e2, "ok": null}`, "json");
    expect(kinds(t, "property")).toEqual(['"name"', '"age"', '"ok"']);
    expect(kinds(t, "string")).toEqual(['"Ada"']);
    expect(kinds(t, "number")).toEqual(["-3.5e2"]);
    expect(kinds(t, "literal")).toEqual(["null"]);
  });

  it("leaves text unhighlighted and merges adjacent plain tokens", () => {
    expect(highlight("just words", "text")).toEqual([{ kind: "plain", text: "just words" }]);
  });

  it("copes with unterminated strings", () => {
    const t = highlight(`x = "oops\ny = 1`, "python");
    expect(kinds(t, "string")).toEqual(['"oops']);
    expect(kinds(t, "number")).toEqual(["1"]);
  });
});

describe("toLines", () => {
  it("splits multi-line tokens across lines", () => {
    const lines = toLines(highlight("/* a\nb */\nx", "javascript"));
    expect(lines).toHaveLength(3);
    expect(lines[0]).toEqual([{ kind: "comment", text: "/* a" }]);
    expect(lines[1]).toEqual([{ kind: "comment", text: "b */" }]);
  });
  it("keeps empty lines", () => {
    expect(toLines(highlight("a\n\nb", "text"))).toHaveLength(3);
  });
});
