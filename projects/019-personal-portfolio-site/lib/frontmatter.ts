/**
 * Minimal YAML-style front-matter parser.
 *
 * Supports the subset a blog actually needs:
 *   ---
 *   title: Hello "world"
 *   date: 2026-01-15
 *   tags: [nextjs, react]
 *   draft: false
 *   ---
 *
 * Values are typed as string | number | boolean | string[]. Writing our own
 * (instead of pulling in gray-matter/js-yaml) keeps the dependency tree small
 * and shows how a line-oriented key/value grammar is tokenised.
 */

export type FrontmatterValue = string | number | boolean | string[];
export type Frontmatter = Record<string, FrontmatterValue>;

export interface ParsedDocument {
  data: Frontmatter;
  content: string;
}

const FENCE = /^---\s*$/;

/** Strip one layer of matching single or double quotes. */
function unquote(raw: string): string {
  const s = raw.trim();
  if (s.length >= 2 && (s[0] === '"' || s[0] === "'") && s[s.length - 1] === s[0]) {
    return s.slice(1, -1);
  }
  return s;
}

/** Convert a scalar literal into its most specific type. */
export function parseScalar(raw: string): FrontmatterValue {
  const s = raw.trim();
  if (s.startsWith("[") && s.endsWith("]")) {
    const inner = s.slice(1, -1).trim();
    return inner === "" ? [] : inner.split(",").map((part) => unquote(part)).filter(Boolean);
  }
  if (s === "true") return true;
  if (s === "false") return false;
  // Numbers only when the whole token is numeric (so "2026-01-15" stays a string).
  if (/^-?\d+(\.\d+)?$/.test(s)) return Number(s);
  return unquote(s);
}

export function parseFrontmatter(source: string): ParsedDocument {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  if (lines.length === 0 || !FENCE.test(lines[0])) {
    return { data: {}, content: source };
  }

  const end = lines.findIndex((line, i) => i > 0 && FENCE.test(line));
  if (end === -1) {
    throw new Error("Unterminated front matter: missing closing '---'");
  }

  const data: Frontmatter = {};
  for (let i = 1; i < end; i++) {
    const line = lines[i];
    if (line.trim() === "" || line.trimStart().startsWith("#")) continue;
    const colon = line.indexOf(":");
    if (colon <= 0) {
      throw new Error(`Invalid front matter on line ${i + 1}: "${line}"`);
    }
    const key = line.slice(0, colon).trim();
    data[key] = parseScalar(line.slice(colon + 1));
  }

  return { data, content: lines.slice(end + 1).join("\n").replace(/^\n+/, "") };
}
