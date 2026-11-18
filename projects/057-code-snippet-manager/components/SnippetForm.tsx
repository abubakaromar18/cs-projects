"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { LANGUAGES, type Language, type Snippet } from "@/lib/types";
import { CodeBlock } from "./CodeBlock";

/** Create (no `snippet`) or edit (with `snippet`) form with a live preview. */
export function SnippetForm({ snippet }: { snippet?: Snippet }) {
  const router = useRouter();
  const [title, setTitle] = useState(snippet?.title ?? "");
  const [description, setDescription] = useState(snippet?.description ?? "");
  const [language, setLanguage] = useState<Language>(snippet?.language ?? "typescript");
  const [code, setCode] = useState(snippet?.code ?? "");
  const [tags, setTags] = useState(snippet?.tags.join(", ") ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const res = await fetch(snippet ? `/api/snippets/${snippet.id}` : "/api/snippets", {
      method: snippet ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description, language, code, tags }),
    });
    const data = await res.json().catch(() => ({}));
    setBusy(false);
    if (!res.ok) {
      setErrors(data.errors ?? { form: "Something went wrong." });
      return;
    }
    router.push(`/snippets/${data.id}`);
    router.refresh();
  }

  // Tab inserts two spaces instead of leaving the textarea.
  function onCodeKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const el = e.currentTarget;
    const { selectionStart: a, selectionEnd: b } = el;
    const next = code.slice(0, a) + "  " + code.slice(b);
    setCode(next);
    requestAnimationFrame(() => el.setSelectionRange(a + 2, a + 2));
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      {errors.form && <p className="error">{errors.form}</p>}
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        {errors.title && <span className="error">{errors.title}</span>}
      </label>
      <label>
        Description
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
        {errors.description && <span className="error">{errors.description}</span>}
      </label>
      <div className="row">
        <label>
          Language
          <select value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
            {LANGUAGES.map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
        </label>
        <label className="grow">
          Tags (comma separated)
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="git, cli" />
          {errors.tags && <span className="error">{errors.tags}</span>}
        </label>
      </div>
      <label>
        Code
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={onCodeKey}
          rows={12}
          spellCheck={false}
          required
        />
        {errors.code && <span className="error">{errors.code}</span>}
      </label>
      {code && (
        <>
          <h3>Preview</h3>
          <CodeBlock code={code} language={language} />
        </>
      )}
      <button className="btn primary" disabled={busy}>
        {snippet ? "Save changes" : "Create snippet"}
      </button>
    </form>
  );
}
