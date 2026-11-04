// Level definitions. Each level sets the tick speed, how much food is needed
// to advance, and a set of static wall cells generated for the given grid.
//
// Walls are produced by small pure functions so levels scale to any grid
// size and are easy to unit-test.

/** @typedef {{x:number, y:number}} Point */

/** Horizontal run of cells from (x0..x1, y). */
function hLine(x0, x1, y) {
  const cells = [];
  for (let x = x0; x <= x1; x++) cells.push({ x, y });
  return cells;
}

/** Vertical run of cells from (x, y0..y1). */
function vLine(x, y0, y1) {
  const cells = [];
  for (let y = y0; y <= y1; y++) cells.push({ x, y });
  return cells;
}

/** Full border around the grid. */
function border(w, h) {
  return [
    ...hLine(0, w - 1, 0),
    ...hLine(0, w - 1, h - 1),
    ...vLine(0, 1, h - 2),
    ...vLine(w - 1, 1, h - 2),
  ];
}

export const LEVELS = [
  {
    name: 'Open Field',
    tickMs: 140,
    foodToAdvance: 5,
    wrap: true, // edges wrap around
    walls: () => [],
  },
  {
    name: 'Fenced In',
    tickMs: 120,
    foodToAdvance: 6,
    wrap: false,
    walls: (w, h) => border(w, h),
  },
  {
    name: 'Twin Bars',
    tickMs: 105,
    foodToAdvance: 7,
    wrap: false,
    walls: (w, h) => {
      const y1 = Math.floor(h / 3);
      const y2 = Math.floor((2 * h) / 3);
      const pad = Math.floor(w / 5);
      return [...border(w, h), ...hLine(pad, w - 1 - pad, y1), ...hLine(pad, w - 1 - pad, y2)];
    },
  },
  {
    name: 'The Cross',
    tickMs: 90,
    foodToAdvance: 8,
    wrap: true,
    walls: (w, h) => {
      const cx = Math.floor(w / 2);
      const cy = Math.floor(h / 2);
      const armX = Math.floor(w / 4);
      const armY = Math.floor(h / 4);
      // Leave the exact centre gap-free but keep the edges open (wrap mode).
      return [...hLine(cx - armX, cx + armX, cy), ...vLine(cx, cy - armY, cy - 1), ...vLine(cx, cy + 1, cy + armY)];
    },
  },
  {
    name: 'Rooms',
    tickMs: 75,
    foodToAdvance: Infinity, // final level: play for score
    wrap: false,
    walls: (w, h) => {
      const cx = Math.floor(w / 2);
      const cy = Math.floor(h / 2);
      const gap = 2; // doorway half-width
      const cells = [...border(w, h)];
      for (let y = 1; y < h - 1; y++) if (Math.abs(y - cy) > gap) cells.push({ x: cx, y });
      for (let x = 1; x < w - 1; x++) if (Math.abs(x - cx) > gap && x !== cx) cells.push({ x, y: cy });
      return cells;
    },
  },
];

/** Clamp a level index into the valid range. */
export function levelAt(index) {
  return LEVELS[Math.max(0, Math.min(index, LEVELS.length - 1))];
}
