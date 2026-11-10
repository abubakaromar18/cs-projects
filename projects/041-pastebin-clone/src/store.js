/**
 * In-memory paste store with time-based expiry.
 *
 * Expiry is enforced two ways:
 *   1. Lazily — every read checks the paste's deadline, so an expired paste is
 *      never served even if the sweeper hasn't run yet.
 *   2. Eagerly — `sweep()` walks a min-heap ordered by expiry time and evicts
 *      everything whose deadline has passed. This bounds memory use without
 *      scanning the whole map: each sweep costs O(k log n) for k expired pastes.
 *
 * The clock is injectable so tests can move time forward deterministically.
 */
import { timingSafeEqual } from 'node:crypto';
import { generateId } from './ids.js';

/** Constant-time string comparison so token checks don't leak timing info. */
function safeEqual(a, b) {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

/** Binary min-heap of { id, expiresAt } keyed on expiresAt. */
class ExpiryHeap {
  constructor() {
    this.items = [];
  }

  get size() {
    return this.items.length;
  }

  peek() {
    return this.items[0];
  }

  push(item) {
    this.items.push(item);
    this.#siftUp(this.items.length - 1);
  }

  pop() {
    const top = this.items[0];
    const last = this.items.pop();
    if (this.items.length > 0) {
      this.items[0] = last;
      this.#siftDown(0);
    }
    return top;
  }

  #siftUp(i) {
    const a = this.items;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (a[parent].expiresAt <= a[i].expiresAt) break;
      [a[parent], a[i]] = [a[i], a[parent]];
      i = parent;
    }
  }

  #siftDown(i) {
    const a = this.items;
    const n = a.length;
    for (;;) {
      const l = 2 * i + 1;
      const r = l + 1;
      let smallest = i;
      if (l < n && a[l].expiresAt < a[smallest].expiresAt) smallest = l;
      if (r < n && a[r].expiresAt < a[smallest].expiresAt) smallest = r;
      if (smallest === i) break;
      [a[smallest], a[i]] = [a[i], a[smallest]];
      i = smallest;
    }
  }
}

export class PasteStore {
  /**
   * @param {object} [opts]
   * @param {() => number} [opts.now]   clock returning epoch milliseconds
   * @param {number} [opts.maxPastes]   hard cap on stored pastes
   * @param {number} [opts.idLength]    length of generated ids
   */
  constructor({ now = Date.now, maxPastes = 10_000, idLength = 8 } = {}) {
    this.now = now;
    this.maxPastes = maxPastes;
    this.idLength = idLength;
    this.pastes = new Map();
    this.heap = new ExpiryHeap();
  }

  get size() {
    return this.pastes.size;
  }

  /**
   * Create a paste.
   * @param {object} input
   * @param {string} input.content
   * @param {string} [input.title]
   * @param {string} [input.language]   highlight.js language name, or 'auto'/'plaintext'
   * @param {number|null} [input.ttlMs] lifetime in ms; null means never expires
   * @param {boolean} [input.burnAfterRead] delete after the first view
   * @returns {object} the stored paste
   */
  create({ content, title = '', language = 'auto', ttlMs = null, burnAfterRead = false }) {
    this.sweep();
    if (this.pastes.size >= this.maxPastes) {
      throw new StoreFullError(this.maxPastes);
    }

    // Retry on the (astronomically unlikely) collision rather than overwrite.
    let id;
    do {
      id = generateId(this.idLength);
    } while (this.pastes.has(id));

    const createdAt = this.now();
    const paste = {
      id,
      title,
      content,
      language,
      createdAt,
      expiresAt: ttlMs == null ? null : createdAt + ttlMs,
      burnAfterRead,
      views: 0,
      // Secret handed only to the creator; required to delete the paste early.
      deleteToken: generateId(24),
    };
    this.pastes.set(id, paste);
    if (paste.expiresAt !== null) {
      this.heap.push({ id, expiresAt: paste.expiresAt });
    }
    return { ...paste };
  }

  /** Look up a paste without counting a view. Returns null if missing/expired. */
  peek(id) {
    const paste = this.pastes.get(id);
    if (!paste) return null;
    if (this.#isExpired(paste)) {
      this.pastes.delete(id);
      return null;
    }
    return { ...paste };
  }

  /**
   * Read a paste, counting a view. Burn-after-read pastes are deleted here,
   * so the caller receives the content exactly once.
   */
  view(id) {
    const paste = this.pastes.get(id);
    if (!paste) return null;
    if (this.#isExpired(paste)) {
      this.pastes.delete(id);
      return null;
    }
    paste.views += 1;
    if (paste.burnAfterRead) {
      this.pastes.delete(id);
    }
    return { ...paste };
  }

  /**
   * Delete a paste if `token` matches its delete token.
   * @returns {'deleted'|'not_found'|'forbidden'}
   */
  deleteWithToken(id, token) {
    const paste = this.peek(id);
    if (!paste) return 'not_found';
    if (!safeEqual(paste.deleteToken, String(token ?? ''))) return 'forbidden';
    this.pastes.delete(id);
    return 'deleted';
  }

  delete(id) {
    return this.pastes.delete(id);
  }

  /** Most recent non-expired, non-burn pastes, newest first. */
  recent(limit = 10) {
    this.sweep();
    return [...this.pastes.values()]
      .filter((p) => !p.burnAfterRead)
      .sort((a, b) => b.createdAt - a.createdAt)
      .slice(0, limit)
      .map((p) => ({ ...p }));
  }

  /** Evict every paste whose deadline has passed. Returns the number removed. */
  sweep() {
    const now = this.now();
    let removed = 0;
    while (this.heap.size > 0 && this.heap.peek().expiresAt <= now) {
      const { id, expiresAt } = this.heap.pop();
      const paste = this.pastes.get(id);
      // The heap may hold stale entries for pastes already deleted (burned,
      // manually removed, or lazily expired) — only count real evictions.
      if (paste && paste.expiresAt === expiresAt) {
        this.pastes.delete(id);
        removed += 1;
      }
    }
    return removed;
  }

  #isExpired(paste) {
    return paste.expiresAt !== null && paste.expiresAt <= this.now();
  }
}

export class StoreFullError extends Error {
  constructor(max) {
    super(`Paste store is full (max ${max} pastes)`);
    this.name = 'StoreFullError';
  }
}
