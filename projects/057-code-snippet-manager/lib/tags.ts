import type { Snippet } from "./types";

/**
 * Canonical tag form: lowercase, trimmed, inner whitespace collapsed to "-",
 * only [a-z0-9-+#.] kept (so "C++", "C#" and "node.js" survive).
 * Duplicates are removed while preserving first-seen order.
 */
export function normalizeTag(tag: string): string {
  return tag
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9\-+#.]/g, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function normalizeTags(tags: string[]): string[] {
  const seen = new Set<string>();
  for (const t of tags) {
    const n = normalizeTag(t);
    if (n) seen.add(n);
  }
  return [...seen];
}

export interface TagCount {
  tag: string;
  count: number;
}

/** Tag cloud data: counts per tag, most-used first, ties broken alphabetically. */
export function countTags(snippets: Snippet[]): TagCount[] {
  const counts = new Map<string, number>();
  for (const s of snippets) for (const t of s.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
  return [...counts]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}
