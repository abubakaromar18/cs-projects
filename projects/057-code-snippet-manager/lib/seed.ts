import type { Snippet } from "./types";

const T = "2026-01-01T00:00:00.000Z";

/** Example snippets written to the data file on first run. */
export const SEED_SNIPPETS: Snippet[] = [
  {
    id: "seed-debounce",
    title: "Debounce a function",
    description: "Delay calls until the caller has been quiet for `ms` milliseconds.",
    language: "typescript",
    tags: ["javascript", "timing", "utility"],
    code: `export function debounce<T extends unknown[]>(fn: (...args: T) => void, ms = 250) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (...args: T) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}`,
    createdAt: T,
    updatedAt: T,
  },
  {
    id: "seed-lru",
    title: "LRU cache with OrderedDict",
    description: "O(1) get/put least-recently-used cache.",
    language: "python",
    tags: ["data-structures", "cache"],
    code: `from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return None
        self.data.move_to_end(key)  # mark as recently used
        return self.data[key]

    def put(self, key, value):
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)`,
    createdAt: T,
    updatedAt: T,
  },
  {
    id: "seed-top-n",
    title: "Top N rows per group",
    description: "Window function to keep the 3 most recent orders per customer.",
    language: "sql",
    tags: ["sql", "window-functions"],
    code: `SELECT *
FROM (
  SELECT o.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
  FROM orders o
) ranked
WHERE rn <= 3; -- keep the newest three`,
    createdAt: T,
    updatedAt: T,
  },
  {
    id: "seed-git-cleanup",
    title: "Delete merged git branches",
    description: "Remove local branches already merged into main.",
    language: "bash",
    tags: ["git", "cli"],
    code: `#!/usr/bin/env bash
set -euo pipefail
git branch --merged main | grep -v '^\\*\\|main' | xargs -r git branch -d
echo "Done cleaning in $PWD"`,
    createdAt: T,
    updatedAt: T,
  },
];
