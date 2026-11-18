import type { Snippet } from "./types";

/**
 * Ranked full-text search over snippets.
 *
 * We build an *inverted index*: term -> (snippet id -> weighted term frequency).
 * Each field contributes with a different weight, so a hit in the title counts
 * more than one buried in the code. Scores use TF-IDF:
 *
 *   score(doc) = Σ over query terms  weightedTf(term, doc) · idf(term)
 *   idf(term)  = ln(1 + N / df(term))
 *
 * The last query term is matched as a *prefix* ("debou" finds "debounce"), which
 * makes search-as-you-type feel natural. All other terms must match exactly
 * (after tokenisation), and every term must match for a snippet to be returned
 * (AND semantics).
 */

export const FIELD_WEIGHTS = {
  title: 5,
  tags: 4,
  description: 2,
  code: 1,
} as const;

type Field = keyof typeof FIELD_WEIGHTS;

/**
 * Split text into lowercase search terms. camelCase and snake_case identifiers
 * are also split into their parts, so "useDebounce" is findable as "debounce".
 */
export function tokenize(text: string): string[] {
  const out: string[] = [];
  for (const word of text.match(/[A-Za-z0-9]+/g) ?? []) {
    const lower = word.toLowerCase();
    out.push(lower);
    const parts = word.split(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/);
    if (parts.length > 1) for (const p of parts) out.push(p.toLowerCase());
  }
  return out;
}

export interface SearchIndex {
  postings: Map<string, Map<string, number>>; // term -> id -> weighted tf
  terms: string[]; // sorted, for prefix lookups
  size: number;
}

export function buildIndex(snippets: Snippet[]): SearchIndex {
  const postings = new Map<string, Map<string, number>>();
  const add = (term: string, id: string, w: number) => {
    let docs = postings.get(term);
    if (!docs) postings.set(term, (docs = new Map()));
    docs.set(id, (docs.get(id) ?? 0) + w);
  };
  for (const s of snippets) {
    const fields: Record<Field, string> = {
      title: s.title,
      tags: s.tags.join(" "),
      description: s.description,
      code: s.code,
    };
    for (const f of Object.keys(fields) as Field[]) {
      for (const term of tokenize(fields[f])) add(term, s.id, FIELD_WEIGHTS[f]);
    }
  }
  return { postings, terms: [...postings.keys()].sort(), size: snippets.length };
}

/** Binary search for the first index whose term is >= prefix. */
function lowerBound(sorted: string[], prefix: string): number {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (sorted[mid] < prefix) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** All index terms starting with `prefix`, found in O(log T + matches). */
export function expandPrefix(index: SearchIndex, prefix: string): string[] {
  const out: string[] = [];
  for (let i = lowerBound(index.terms, prefix); i < index.terms.length; i++) {
    if (!index.terms[i].startsWith(prefix)) break;
    out.push(index.terms[i]);
  }
  return out;
}

/** Score every document matching one query term (or, if prefix, any expansion of it). */
function scoreTerm(index: SearchIndex, term: string, prefix: boolean): Map<string, number> {
  const candidates = prefix ? expandPrefix(index, term) : index.postings.has(term) ? [term] : [];
  const scores = new Map<string, number>();
  for (const t of candidates) {
    const docs = index.postings.get(t)!;
    const idf = Math.log(1 + index.size / docs.size);
    // An exact match beats a prefix expansion of the same length class.
    const bonus = t === term ? 1 : 0.8;
    for (const [id, tf] of docs) {
      // Keep the best expansion per doc so "a" doesn't add up hundreds of terms.
      scores.set(id, Math.max(scores.get(id) ?? 0, tf * idf * bonus));
    }
  }
  return scores;
}

export interface SearchOptions {
  query?: string;
  tags?: string[]; // snippet must carry ALL of these
  language?: string;
}

/**
 * Filter and rank. With no query, results are newest-first; with a query they
 * are by descending score (ties: newest first).
 */
export function search(snippets: Snippet[], opts: SearchOptions, index = buildIndex(snippets)): Snippet[] {
  const wanted = opts.tags ?? [];
  let pool = snippets.filter(
    (s) =>
      wanted.every((t) => s.tags.includes(t)) && (!opts.language || s.language === opts.language),
  );

  const byNewest = (a: Snippet, b: Snippet) => b.updatedAt.localeCompare(a.updatedAt);
  const terms = [...new Set(tokenize(opts.query ?? ""))];
  if (terms.length === 0) return pool.sort(byNewest);

  // The word the user is still typing is matched as a prefix. Tokenising it
  // ("useDeb" -> usedeb, use, deb) can yield several terms; all count as prefixes.
  const rawWords = (opts.query ?? "").trim().split(/\s+/);
  const prefixTerms = new Set(tokenize(rawWords[rawWords.length - 1]));

  const total = new Map<string, number>();
  for (const id of pool.map((s) => s.id)) total.set(id, 0);
  for (const term of terms) {
    const scores = scoreTerm(index, term, prefixTerms.has(term));
    for (const id of [...total.keys()]) {
      const s = scores.get(id);
      if (s === undefined) total.delete(id); // AND semantics
      else total.set(id, total.get(id)! + s);
    }
  }
  pool = pool.filter((s) => total.has(s.id));
  return pool.sort((a, b) => total.get(b.id)! - total.get(a.id)! || byNewest(a, b));
}
