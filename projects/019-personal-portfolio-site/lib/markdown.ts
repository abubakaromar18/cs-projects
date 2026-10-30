/**
 * A small, safe Markdown → HTML renderer.
 *
 * Block grammar (processed line by line, a simple state machine):
 *   # .. ######   headings          ```lang ... ```  fenced code
 *   - item / * item unordered list  1. item          ordered list
 *   > quote       blockquote        ---              horizontal rule
 *   blank line    paragraph break
 *
 * Inline grammar: `code`, **bold**, *italic*, [text](url).
 *
 * SECURITY: every piece of user text is HTML-escaped *before* inline markup is
 * applied, and link targets are restricted to http(s), mailto and relative
 * URLs, so posts can never inject <script> or javascript: links.
 */

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function isSafeUrl(url: string): boolean {
  const u = url.trim().toLowerCase();
  return /^(https?:|mailto:)/.test(u) || u.startsWith("/") || u.startsWith("#") || !/^[a-z][a-z0-9+.-]*:/.test(u);
}

/** Render inline markup on a single line of (unescaped) text. */
export function renderInline(text: string): string {
  // Pull out code spans first so their contents are not further formatted.
  const codeSpans: string[] = [];
  let out = text.replace(/`([^`]+)`/g, (_, code: string) => {
    codeSpans.push(`<code>${escapeHtml(code)}</code>`);
    return `\u0000${codeSpans.length - 1}\u0000`;
  });

  out = escapeHtml(out);

  out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label: string, href: string) => {
    // href was escaped above; un-escape &amp; for the safety check only.
    const raw = href.replace(/&amp;/g, "&");
    if (!isSafeUrl(raw)) return label;
    const external = /^https?:/i.test(raw);
    const attrs = external ? ' target="_blank" rel="noopener noreferrer"' : "";
    return `<a href="${href}"${attrs}>${label}</a>`;
  });
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");

  return out.replace(/\u0000(\d+)\u0000/g, (_, i: string) => codeSpans[Number(i)]);
}

type ListKind = "ul" | "ol";

export function renderMarkdown(source: string): string {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const html: string[] = [];

  let paragraph: string[] = [];
  let list: { kind: ListKind; items: string[] } | null = null;
  let quote: string[] = [];
  let code: { lang: string; lines: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length) html.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (list) html.push(`<${list.kind}>${list.items.map((i) => `<li>${renderInline(i)}</li>`).join("")}</${list.kind}>`);
    list = null;
  };
  const flushQuote = () => {
    if (quote.length) html.push(`<blockquote><p>${renderInline(quote.join(" "))}</p></blockquote>`);
    quote = [];
  };
  const flushAll = () => {
    flushParagraph();
    flushList();
    flushQuote();
  };

  for (const line of lines) {
    // Inside a fenced code block everything is literal until the closing fence.
    if (code) {
      if (/^```\s*$/.test(line)) {
        const cls = code.lang ? ` class="language-${escapeHtml(code.lang)}"` : "";
        html.push(`<pre><code${cls}>${escapeHtml(code.lines.join("\n"))}</code></pre>`);
        code = null;
      } else {
        code.lines.push(line);
      }
      continue;
    }

    const fence = line.match(/^```\s*([\w+-]*)\s*$/);
    if (fence) {
      flushAll();
      code = { lang: fence[1], lines: [] };
      continue;
    }

    if (line.trim() === "") {
      flushAll();
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushAll();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInline(heading[2].trim())}</h${level}>`);
      continue;
    }

    if (/^(-{3,}|\*{3,})\s*$/.test(line)) {
      flushAll();
      html.push("<hr />");
      continue;
    }

    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ul || ol) {
      const kind: ListKind = ul ? "ul" : "ol";
      flushParagraph();
      flushQuote();
      if (list && list.kind !== kind) flushList();
      if (!list) list = { kind, items: [] };
      list.items.push((ul ?? ol)![1]);
      continue;
    }

    const bq = line.match(/^>\s?(.*)$/);
    if (bq) {
      flushParagraph();
      flushList();
      quote.push(bq[1]);
      continue;
    }

    flushList();
    flushQuote();
    paragraph.push(line.trim());
  }

  // Unclosed code fence: render what we have rather than dropping content.
  if (code) html.push(`<pre><code>${escapeHtml(code.lines.join("\n"))}</code></pre>`);
  flushAll();
  return html.join("\n");
}
