import fs from "node:fs";
import path from "node:path";
import { parseFrontmatter, type Frontmatter } from "./frontmatter";
import { renderMarkdown } from "./markdown";

export interface PostMeta {
  slug: string;
  title: string;
  date: string; // ISO yyyy-mm-dd
  summary: string;
  tags: string[];
  readingMinutes: number;
}

export interface Post extends PostMeta {
  html: string;
}

export const POSTS_DIR = path.join(process.cwd(), "content", "posts");

const WORDS_PER_MINUTE = 200;

/** "My First Post!" -> "my-first-post" */
export function slugify(input: string): string {
  return input
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function readingTime(markdown: string): number {
  const words = markdown.replace(/```[\s\S]*?```/g, " ").split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

function requireString(data: Frontmatter, key: string, file: string): string {
  const v = data[key];
  if (typeof v !== "string" || v.trim() === "") {
    throw new Error(`${file}: front matter field "${key}" is required`);
  }
  return v;
}

/** Turn a raw markdown file into a typed Post. Pure, so it is easy to unit test. */
export function parsePost(fileName: string, source: string): Post & { draft: boolean } {
  const { data, content } = parseFrontmatter(source);
  const date = requireString(data, "date", fileName);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date))) {
    throw new Error(`${fileName}: invalid date "${date}" (expected YYYY-MM-DD)`);
  }
  const tags = Array.isArray(data.tags) ? data.tags : [];
  return {
    slug: slugify(fileName.replace(/\.md$/, "")),
    title: requireString(data, "title", fileName),
    date,
    summary: typeof data.summary === "string" ? data.summary : "",
    tags,
    readingMinutes: readingTime(content),
    draft: data.draft === true,
    html: renderMarkdown(content),
  };
}

/** Newest first; ties broken by title so ordering is deterministic. */
export function sortPosts<T extends PostMeta>(posts: T[]): T[] {
  return [...posts].sort((a, b) => b.date.localeCompare(a.date) || a.title.localeCompare(b.title));
}

export function getAllPosts(dir: string = POSTS_DIR): Post[] {
  if (!fs.existsSync(dir)) return [];
  const posts = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => parsePost(f, fs.readFileSync(path.join(dir, f), "utf8")))
    .filter((p) => !p.draft)
    .map(({ draft: _draft, ...post }) => post);
  return sortPosts(posts);
}

export function getPostBySlug(slug: string, dir: string = POSTS_DIR): Post | undefined {
  return getAllPosts(dir).find((p) => p.slug === slug);
}

export function formatDate(iso: string): string {
  // Parse as UTC so the rendered day never shifts with the server's timezone.
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}
