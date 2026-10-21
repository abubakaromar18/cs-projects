/**
 * Session statistics: an append-only log of completed phases plus pure
 * aggregation functions. Persistence is delegated to a storage adapter so the
 * same code runs against localStorage in the browser and a Map in tests.
 */

const STORAGE_KEY = 'pomodoro.sessions.v1';
const DAY = 86_400_000;

/** Local calendar date as YYYY-MM-DD (avoids UTC off-by-one at night). */
export function dayKey(timestamp) {
  const d = new Date(timestamp);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

/** Group work sessions by day: { 'YYYY-MM-DD': { sessions, focusMs } }. */
export function groupByDay(sessions) {
  const days = {};
  for (const s of sessions) {
    if (s.phase !== 'work') continue;
    const key = dayKey(s.at);
    days[key] ??= { sessions: 0, focusMs: 0 };
    days[key].sessions += 1;
    days[key].focusMs += s.duration;
  }
  return days;
}

/**
 * Consecutive days (ending today, or yesterday if nothing yet today)
 * with at least one completed work session.
 */
export function currentStreak(sessions, now = Date.now()) {
  const days = groupByDay(sessions);
  let cursor = now;
  if (!days[dayKey(cursor)]) cursor -= DAY; // today not started yet: streak still alive
  let streak = 0;
  while (days[dayKey(cursor)]) {
    streak += 1;
    cursor -= DAY;
  }
  return streak;
}

/** Last `n` days (oldest first) for a bar chart, including empty days. */
export function lastNDays(sessions, n = 7, now = Date.now()) {
  const days = groupByDay(sessions);
  const out = [];
  for (let i = n - 1; i >= 0; i--) {
    const key = dayKey(now - i * DAY);
    out.push({ day: key, ...(days[key] ?? { sessions: 0, focusMs: 0 }) });
  }
  return out;
}

/** Headline numbers for the stats panel. */
export function summarize(sessions, now = Date.now()) {
  const days = groupByDay(sessions);
  const today = days[dayKey(now)] ?? { sessions: 0, focusMs: 0 };
  const work = sessions.filter((s) => s.phase === 'work');
  return {
    todaySessions: today.sessions,
    todayFocusMinutes: Math.round(today.focusMs / 60_000),
    totalSessions: work.length,
    totalFocusMinutes: Math.round(work.reduce((t, s) => t + s.duration, 0) / 60_000),
    streak: currentStreak(sessions, now),
  };
}

/** Wraps any Storage-like object ({getItem,setItem,removeItem}). */
export class SessionLog {
  constructor(storage) {
    this.storage = storage;
    this.sessions = this.load();
  }

  load() {
    try {
      const raw = this.storage?.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.filter(isValidSession) : [];
    } catch {
      return []; // corrupted data or storage blocked (private mode)
    }
  }

  save() {
    try {
      this.storage?.setItem(STORAGE_KEY, JSON.stringify(this.sessions));
    } catch {
      /* storage full or unavailable; keep in memory only */
    }
  }

  add({ phase, duration, at }) {
    const entry = { phase, duration, at };
    if (!isValidSession(entry)) throw new TypeError('Invalid session entry');
    this.sessions.push(entry);
    this.save();
    return entry;
  }

  clear() {
    this.sessions = [];
    try { this.storage?.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  }
}

function isValidSession(s) {
  return s && typeof s.phase === 'string'
    && Number.isFinite(s.duration) && s.duration >= 0
    && Number.isFinite(s.at);
}

/** Minimal in-memory Storage implementation (used in tests and as a fallback). */
export class MemoryStorage {
  constructor() { this.map = new Map(); }
  getItem(k) { return this.map.has(k) ? this.map.get(k) : null; }
  setItem(k, v) { this.map.set(k, String(v)); }
  removeItem(k) { this.map.delete(k); }
}
