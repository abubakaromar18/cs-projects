"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { buildIndex, search } from "@/lib/search";
import { countTags } from "@/lib/tags";
import { LANGUAGES, type Snippet } from "@/lib/types";
import { CodeBlock } from "./CodeBlock";
import { CopyButton } from "./CopyButton";

/**
 * Search-as-you-type list. All snippets arrive from the server once; the index
 * is built in the browser and every keystroke re-ranks locally, so filtering
 * is instant. Current filters are mirrored into the URL so views can be
 * bookmarked or shared.
 */
export function SnippetBrowser({
  snippets,
  initial,
}: {
  snippets: Snippet[];
  initial: { q: string; tags: string[]; language: string };
}) {
  const [query, setQuery] = useState(initial.q);
  const [tags, setTags] = useState<string[]>(initial.tags);
  const [language, setLanguage] = useState(initial.language);

  const index = useMemo(() => buildIndex(snippets), [snippets]);
  const tagCounts = useMemo(() => countTags(snippets), [snippets]);
  const results = useMemo(
    () => search(snippets, { query, tags, language: language || undefined }, index),
    [snippets, index, query, tags, language],
  );

  useEffect(() => {
    const p = new URLSearchParams();
    if (query) p.set("q", query);
    for (const t of tags) p.append("tag", t);
    if (language) p.set("language", language);
    const qs = p.toString();
    window.history.replaceState(null, "", qs ? `/?${qs}` : "/");
  }, [query, tags, language]);

  const toggleTag = (t: string) =>
    setTags((cur) => (cur.includes(t) ? cur.filter((x) => x !== t) : [...cur, t]));

  return (
    <div className="browser">
      <aside className="sidebar">
        <h2>Tags</h2>
        {tagCounts.length === 0 && <p className="muted">No tags yet.</p>}
        <ul className="tag-cloud">
          {tagCounts.map(({ tag, count }) => (
            <li key={tag}>
              <button
                type="button"
                className={`tag ${tags.includes(tag) ? "active" : ""}`}
                aria-pressed={tags.includes(tag)}
                onClick={() => toggleTag(tag)}
              >
                #{tag} <span className="count">{count}</span>
              </button>
            </li>
          ))}
        </ul>
        {tags.length > 0 && (
          <button type="button" className="btn small" onClick={() => setTags([])}>
            Clear tags
          </button>
        )}
      </aside>

      <section>
        <div className="filters">
          <input
            type="search"
            placeholder="Search titles, tags, code…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search snippets"
            autoFocus
          />
          <select value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Language">
            <option value="">All languages</option>
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <p className="muted">
          {results.length} of {snippets.length} snippets
        </p>

        {results.map((s) => (
          <article key={s.id} className="card">
            <header>
              <h3>
                <Link href={`/snippets/${s.id}`}>{s.title}</Link>
              </h3>
              <span className="lang">{s.language}</span>
              <CopyButton text={s.code} />
            </header>
            {s.description && <p className="desc">{s.description}</p>}
            <CodeBlock code={s.code} language={s.language} maxLines={8} />
            <ul className="tags">
              {s.tags.map((t) => (
                <li key={t}>
                  <button type="button" className="tag" onClick={() => toggleTag(t)}>
                    #{t}
                  </button>
                </li>
              ))}
            </ul>
          </article>
        ))}
        {results.length === 0 && <p className="empty">No snippets match.</p>}
      </section>
    </div>
  );
}
