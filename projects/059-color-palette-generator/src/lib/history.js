/**
 * Immutable undo/redo history (the classic "two stacks" design).
 *
 *   past    — states before `present`, oldest first
 *   present — the current state
 *   future  — states undone, nearest first
 *
 * Pushing a new state clears `future` (you can't redo after branching).
 * `limit` caps memory use by discarding the oldest entries.
 */
export function createHistory(initial, limit = 50) {
  return { past: [], present: initial, future: [], limit };
}

export function push(h, state) {
  const past = [...h.past, h.present];
  if (past.length > h.limit) past.shift();
  return { ...h, past, present: state, future: [] };
}

export function undo(h) {
  if (h.past.length === 0) return h;
  const past = h.past.slice(0, -1);
  return { ...h, past, present: h.past[h.past.length - 1], future: [h.present, ...h.future] };
}

export function redo(h) {
  if (h.future.length === 0) return h;
  const [next, ...future] = h.future;
  return { ...h, past: [...h.past, h.present], present: next, future };
}

export const canUndo = (h) => h.past.length > 0;
export const canRedo = (h) => h.future.length > 0;
