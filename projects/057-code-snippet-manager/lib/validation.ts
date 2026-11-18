import { LANGUAGES, type Language, type SnippetInput } from "./types";
import { normalizeTags } from "./tags";

export const LIMITS = {
  title: 120,
  description: 500,
  code: 20_000,
  tags: 10,
} as const;

export type ValidationResult =
  | { ok: true; value: SnippetInput }
  | { ok: false; errors: Record<string, string> };

function isLanguage(x: unknown): x is Language {
  return typeof x === "string" && (LANGUAGES as readonly string[]).includes(x);
}

/**
 * Validate untrusted JSON (from a request body) and return a clean SnippetInput.
 * Every error is collected rather than failing fast, so a form can show them all.
 */
export function validateSnippet(raw: unknown): ValidationResult {
  const errors: Record<string, string> = {};
  const body = (typeof raw === "object" && raw !== null ? raw : {}) as Record<string, unknown>;

  const title = typeof body.title === "string" ? body.title.trim() : "";
  if (!title) errors.title = "Title is required.";
  else if (title.length > LIMITS.title) errors.title = `Title must be at most ${LIMITS.title} characters.`;

  const description = typeof body.description === "string" ? body.description.trim() : "";
  if (description.length > LIMITS.description)
    errors.description = `Description must be at most ${LIMITS.description} characters.`;

  const language = body.language ?? "text";
  if (!isLanguage(language)) errors.language = `Language must be one of: ${LANGUAGES.join(", ")}.`;

  // Keep the code's internal whitespace exactly; only drop trailing blank lines.
  const code = typeof body.code === "string" ? body.code.replace(/\s+$/, "") : "";
  if (!code) errors.code = "Code is required.";
  else if (code.length > LIMITS.code) errors.code = `Code must be at most ${LIMITS.code} characters.`;

  let tagSource: unknown = body.tags ?? [];
  if (typeof tagSource === "string") tagSource = tagSource.split(",");
  if (!Array.isArray(tagSource) || !tagSource.every((t) => typeof t === "string")) {
    errors.tags = "Tags must be a list of strings.";
    tagSource = [];
  }
  const tags = normalizeTags(tagSource as string[]);
  if (tags.length > LIMITS.tags) errors.tags = `At most ${LIMITS.tags} tags.`;

  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, value: { title, description, language: language as Language, code, tags } };
}
