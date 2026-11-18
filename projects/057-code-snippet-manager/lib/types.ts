/** Languages the highlighter understands. "text" means "no highlighting". */
export const LANGUAGES = [
  "javascript",
  "typescript",
  "python",
  "go",
  "rust",
  "bash",
  "sql",
  "json",
  "text",
] as const;

export type Language = (typeof LANGUAGES)[number];

export interface Snippet {
  id: string;
  title: string;
  description: string;
  language: Language;
  code: string;
  tags: string[];
  createdAt: string; // ISO-8601
  updatedAt: string; // ISO-8601
}

/** The fields a client may send when creating or updating a snippet. */
export type SnippetInput = Pick<Snippet, "title" | "description" | "language" | "code" | "tags">;
