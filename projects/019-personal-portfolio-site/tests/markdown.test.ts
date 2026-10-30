import { describe, expect, it } from "vitest";
import { escapeHtml, isSafeUrl, renderInline, renderMarkdown } from "@/lib/markdown";

describe("inline rendering", () => {
  it("formats bold, italic, code and links", () => {
    expect(renderInline("**b** and *i*")).toBe("<strong>b</strong> and <em>i</em>");
    expect(renderInline("use `a < b`")).toBe("use <code>a &lt; b</code>");
    expect(renderInline("[home](/)")).toBe('<a href="/">home</a>');
    expect(renderInline("[x](https://e.com)")).toBe('<a href="https://e.com" target="_blank" rel="noopener noreferrer">x</a>');
  });

  it("does not format inside code spans", () => {
    expect(renderInline("`**not bold**`")).toBe("<code>**not bold**</code>");
  });
});

describe("XSS safety", () => {
  it("escapes raw HTML", () => {
    expect(escapeHtml(`<a href="x">'&'</a>`)).toBe("&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
    expect(renderMarkdown("<script>alert(1)</script>")).toBe("<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>");
  });

  it("drops javascript: and data: links but keeps the label", () => {
    expect(renderInline("[click](javascript:alert(1))")).not.toContain("href");
    expect(renderInline("[img](data:text/html;base64,xx)")).toBe("img");
    expect(isSafeUrl("JavaScript:alert(1)")).toBe(false);
    expect(isSafeUrl("mailto:a@b.co")).toBe(true);
    expect(isSafeUrl("../relative")).toBe(true);
  });
});

describe("block rendering", () => {
  it("renders headings, paragraphs and lists", () => {
    const html = renderMarkdown("# Title\n\nline one\nline two\n\n- a\n- b\n\n1. x\n2. y");
    expect(html).toBe("<h1>Title</h1>\n<p>line one line two</p>\n<ul><li>a</li><li>b</li></ul>\n<ol><li>x</li><li>y</li></ol>");
  });

  it("keeps fenced code literal and escaped", () => {
    const html = renderMarkdown("```ts\nconst a = 1 < 2; // **no**\n```");
    expect(html).toBe('<pre><code class="language-ts">const a = 1 &lt; 2; // **no**</code></pre>');
  });

  it("renders blockquotes and rules", () => {
    expect(renderMarkdown("> quoted *text*\n\n---")).toBe("<blockquote><p>quoted <em>text</em></p></blockquote>\n<hr />");
  });

  it("switches list type without merging", () => {
    expect(renderMarkdown("- a\n1. b")).toBe("<ul><li>a</li></ul>\n<ol><li>b</li></ol>");
  });

  it("does not lose content from an unclosed fence", () => {
    expect(renderMarkdown("```\nabc")).toBe("<pre><code>abc</code></pre>");
  });
});
