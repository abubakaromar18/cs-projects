import { promises as fs } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type { Snippet, SnippetInput } from "./types";
import { SEED_SNIPPETS } from "./seed";

/**
 * A tiny JSON-file "database".
 *
 * - Reads parse the whole file (fine for thousands of snippets).
 * - Writes go to a temp file and are then `rename`d over the original. rename
 *   is atomic on POSIX filesystems, so a crash mid-write never leaves a
 *   half-written, corrupt JSON file behind.
 * - All mutations are serialised through a promise chain (a simple async
 *   mutex), so two concurrent POSTs can't read the same old state and
 *   overwrite each other's changes (the "lost update" problem).
 */
export class SnippetStore {
  private queue: Promise<unknown> = Promise.resolve();

  constructor(
    private readonly file: string,
    private readonly now: () => Date = () => new Date(),
  ) {}

  private async readAll(): Promise<Snippet[]> {
    try {
      return JSON.parse(await fs.readFile(this.file, "utf8")) as Snippet[];
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
      // First run: start from the bundled examples.
      await this.writeAll(SEED_SNIPPETS);
      return structuredClone(SEED_SNIPPETS);
    }
  }

  private async writeAll(snippets: Snippet[]): Promise<void> {
    await fs.mkdir(path.dirname(this.file), { recursive: true });
    const tmp = `${this.file}.${process.pid}.${Date.now()}.tmp`;
    await fs.writeFile(tmp, JSON.stringify(snippets, null, 2) + "\n", "utf8");
    await fs.rename(tmp, this.file);
  }

  /** Run `fn` after every previously queued mutation has finished. */
  private exclusive<T>(fn: () => Promise<T>): Promise<T> {
    const run = this.queue.then(fn, fn);
    this.queue = run.catch(() => undefined);
    return run;
  }

  async list(): Promise<Snippet[]> {
    await this.queue;
    return this.readAll();
  }

  async get(id: string): Promise<Snippet | undefined> {
    return (await this.list()).find((s) => s.id === id);
  }

  create(input: SnippetInput): Promise<Snippet> {
    return this.exclusive(async () => {
      const all = await this.readAll();
      const ts = this.now().toISOString();
      const snippet: Snippet = { id: randomUUID(), ...input, createdAt: ts, updatedAt: ts };
      all.push(snippet);
      await this.writeAll(all);
      return snippet;
    });
  }

  update(id: string, input: SnippetInput): Promise<Snippet | undefined> {
    return this.exclusive(async () => {
      const all = await this.readAll();
      const i = all.findIndex((s) => s.id === id);
      if (i === -1) return undefined;
      all[i] = { ...all[i], ...input, id, updatedAt: this.now().toISOString() };
      await this.writeAll(all);
      return all[i];
    });
  }

  remove(id: string): Promise<boolean> {
    return this.exclusive(async () => {
      const all = await this.readAll();
      const next = all.filter((s) => s.id !== id);
      if (next.length === all.length) return false;
      await this.writeAll(next);
      return true;
    });
  }
}

let shared: SnippetStore | undefined;

/** The app-wide store. Location can be overridden with SNIPPETS_FILE. */
export function getStore(): SnippetStore {
  shared ??= new SnippetStore(
    process.env.SNIPPETS_FILE ?? path.join(process.cwd(), "data", "snippets.local.json"),
  );
  return shared;
}
