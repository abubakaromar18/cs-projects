/**
 * Persistence for best score and the in-progress game, behind a minimal
 * Storage-like interface so it works with localStorage or an in-memory map.
 */
import type { Snapshot } from "./game.js";

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export class MemoryStore implements KeyValueStore {
  private data = new Map<string, string>();
  getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
  removeItem(key: string): void {
    this.data.delete(key);
  }
}

const BEST_KEY = "2048.best";
const GAME_KEY = "2048.game";

export class GameStorage {
  constructor(private readonly store: KeyValueStore) {}

  getBest(): number {
    const n = Number(this.safeGet(BEST_KEY));
    return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
  }

  /** Record a score; returns the (possibly updated) best. */
  submitScore(score: number): number {
    const best = Math.max(this.getBest(), score);
    this.safeSet(BEST_KEY, String(best));
    return best;
  }

  saveGame(snapshot: Snapshot): void {
    this.safeSet(GAME_KEY, JSON.stringify(snapshot));
  }

  /** Returns a saved game, or null if none / corrupt. */
  loadGame(): Snapshot | null {
    const raw = this.safeGet(GAME_KEY);
    if (!raw) return null;
    try {
      const s = JSON.parse(raw) as Snapshot;
      if (!isSnapshot(s)) return null;
      return s;
    } catch {
      return null;
    }
  }

  clearGame(): void {
    try {
      this.store.removeItem(GAME_KEY);
    } catch {
      /* storage unavailable — ignore */
    }
  }

  // Storage can throw (private mode, quota); the game must keep working.
  private safeGet(key: string): string | null {
    try {
      return this.store.getItem(key);
    } catch {
      return null;
    }
  }

  private safeSet(key: string, value: string): void {
    try {
      this.store.setItem(key, value);
    } catch {
      /* ignore */
    }
  }
}

function isSnapshot(s: unknown): s is Snapshot {
  if (typeof s !== "object" || s === null) return false;
  const o = s as Record<string, unknown>;
  return (
    typeof o.size === "number" &&
    typeof o.target === "number" &&
    typeof o.score === "number" &&
    typeof o.nextId === "number" &&
    Array.isArray(o.tiles) &&
    o.tiles.every(
      (t: unknown) =>
        typeof t === "object" &&
        t !== null &&
        ["id", "value", "row", "col"].every((k) => typeof (t as Record<string, unknown>)[k] === "number"),
    )
  );
}
