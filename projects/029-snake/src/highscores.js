// High-score table persisted through a Storage-like object (localStorage in
// the browser, an in-memory stub in tests). All access is guarded because
// storage can be unavailable (private mode, blocked cookies).

export const STORAGE_KEY = 'snake.highscores.v1';
export const MAX_ENTRIES = 10;

/** In-memory fallback implementing the bits of the Storage API we use. */
export function memoryStorage() {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
  };
}

/** Validate and normalise one entry; returns null if it's malformed. */
function clean(e) {
  if (!e || typeof e !== 'object') return null;
  const score = Number(e.score);
  if (!Number.isFinite(score) || score < 0) return null;
  const name = String(e.name ?? 'Player').trim().slice(0, 12) || 'Player';
  const level = Number.isInteger(e.level) ? e.level : 0;
  const date = typeof e.date === 'string' ? e.date : new Date(0).toISOString();
  return { name, score: Math.floor(score), level, date };
}

/** Highest score first; ties go to whoever set it earlier. */
const byRank = (a, b) => b.score - a.score || a.date.localeCompare(b.date);

export class HighScores {
  /** @param {{getItem:Function,setItem:Function}} [storage] */
  constructor(storage = memoryStorage()) {
    this.storage = storage;
  }

  /** @returns {{name:string, score:number, level:number, date:string}[]} */
  list() {
    let raw;
    try {
      raw = JSON.parse(this.storage.getItem(STORAGE_KEY) ?? '[]');
    } catch {
      return []; // corrupt JSON: start fresh rather than crash
    }
    if (!Array.isArray(raw)) return [];
    return raw.map(clean).filter(Boolean).sort(byRank).slice(0, MAX_ENTRIES);
  }

  /** Would this score make the table? */
  qualifies(score) {
    if (score <= 0) return false;
    const l = this.list();
    return l.length < MAX_ENTRIES || score > l[l.length - 1].score;
  }

  /** Best score so far, or 0. */
  best() {
    return this.list()[0]?.score ?? 0;
  }

  /**
   * Insert a score. Returns its 0-based rank, or -1 if it didn't place.
   * @param {{name?:string, score:number, level?:number, date?:string}} entry
   */
  add(entry) {
    const e = clean({ date: new Date().toISOString(), ...entry });
    if (!e || !this.qualifies(e.score)) return -1;
    const next = [...this.list(), e].sort(byRank).slice(0, MAX_ENTRIES);
    try {
      this.storage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* quota or disabled storage: keep playing without persistence */
    }
    return next.indexOf(e);
  }

  clear() {
    try {
      this.storage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }
}
