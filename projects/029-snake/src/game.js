// Pure game logic for Snake. No DOM, no timers — the browser layer calls
// `step()` on each tick and renders the resulting state. Keeping logic pure
// makes it deterministic (given an RNG) and trivial to unit-test in Node.

import { LEVELS, levelAt } from './levels.js';

/** @typedef {{x:number, y:number}} Point */

export const DIRS = Object.freeze({
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
});

const OPPOSITE = { up: 'down', down: 'up', left: 'right', right: 'left' };

/** Max buffered turns; lets fast "up, left" input register within one tick. */
const MAX_QUEUED_TURNS = 3;

export const key = (p) => `${p.x},${p.y}`;

/**
 * Create a fresh game.
 * @param {{width?:number, height?:number, level?:number, rng?:() => number}} [opts]
 */
export function createGame({ width = 24, height = 24, level = 0, rng = Math.random } = {}) {
  const state = {
    width,
    height,
    rng,
    level: 0,
    score: 0,
    foodEatenThisLevel: 0,
    totalFood: 0,
    status: 'ready', // ready | running | paused | over | won-level
    snake: [],
    dir: 'right',
    queue: [],
    walls: new Set(),
    food: null,
    growth: 0,
  };
  loadLevel(state, level);
  return state;
}

/** Reset the board for a given level, keeping score. */
export function loadLevel(state, index) {
  const lvl = levelAt(index);
  state.level = Math.max(0, Math.min(index, LEVELS.length - 1));
  state.walls = new Set(lvl.walls(state.width, state.height).map(key));
  state.foodEatenThisLevel = 0;
  state.dir = 'right';
  state.queue = [];
  state.growth = 0;

  // Start with a 3-cell snake heading right, placed on the first clear row
  // at or below one quarter of the height.
  const startX = Math.floor(state.width / 4);
  let startY = Math.floor(state.height / 4);
  while (!rowClear(state, startY, startX - 2, startX) && startY < state.height - 1) startY++;
  state.snake = [
    { x: startX, y: startY },
    { x: startX - 1, y: startY },
    { x: startX - 2, y: startY },
  ];
  state.food = spawnFood(state);
  state.status = 'ready';
  return state;
}

function rowClear(state, y, x0, x1) {
  for (let x = x0; x <= x1; x++) if (state.walls.has(key({ x, y }))) return false;
  return true;
}

/** Current level config. */
export const currentLevel = (state) => levelAt(state.level);

/**
 * Queue a direction change. Rejects reversals (relative to the last queued
 * direction) and duplicates so the snake can never turn back into itself.
 * @returns {boolean} whether the turn was accepted
 */
export function turn(state, dirName) {
  if (!(dirName in DIRS)) return false;
  const last = state.queue.length ? state.queue[state.queue.length - 1] : state.dir;
  if (dirName === last || dirName === OPPOSITE[last]) return false;
  if (state.queue.length >= MAX_QUEUED_TURNS) return false;
  state.queue.push(dirName);
  if (state.status === 'ready') state.status = 'running';
  return true;
}

/** Pick a random empty cell for food, or null if the board is full. */
export function spawnFood(state) {
  const occupied = new Set(state.walls);
  for (const s of state.snake) occupied.add(key(s));
  const free = [];
  for (let y = 0; y < state.height; y++) {
    for (let x = 0; x < state.width; x++) {
      if (!occupied.has(`${x},${y}`)) free.push({ x, y });
    }
  }
  if (free.length === 0) return null;
  return free[Math.floor(state.rng() * free.length)];
}

/** Points per food grow with level so harder levels are worth more. */
export const pointsFor = (levelIndex) => 10 * (levelIndex + 1);

/**
 * Advance the game by one tick.
 * @returns {{ate:boolean, died:boolean, levelUp:boolean}} events for the UI (sound, flashes)
 */
export function step(state) {
  const events = { ate: false, died: false, levelUp: false };
  if (state.status !== 'running') return events;

  if (state.queue.length) state.dir = state.queue.shift();
  const d = DIRS[state.dir];
  const lvl = currentLevel(state);
  const head = state.snake[0];
  let next = { x: head.x + d.x, y: head.y + d.y };

  if (lvl.wrap) {
    next = {
      x: (next.x + state.width) % state.width,
      y: (next.y + state.height) % state.height,
    };
  } else if (next.x < 0 || next.y < 0 || next.x >= state.width || next.y >= state.height) {
    return die(state, events);
  }

  const willEat = state.food && next.x === state.food.x && next.y === state.food.y;
  // The tail cell vacates this tick unless we're growing, so moving into it is legal.
  const tailMoves = state.growth === 0 && !willEat;
  const body = tailMoves ? state.snake.slice(0, -1) : state.snake;
  if (state.walls.has(key(next)) || body.some((s) => s.x === next.x && s.y === next.y)) {
    return die(state, events);
  }

  state.snake.unshift(next);
  if (willEat) {
    events.ate = true;
    state.growth += 1;
    state.score += pointsFor(state.level);
    state.foodEatenThisLevel += 1;
    state.totalFood += 1;
  }
  if (state.growth > 0) state.growth -= 1;
  else state.snake.pop();

  if (willEat) {
    if (state.foodEatenThisLevel >= lvl.foodToAdvance && state.level < LEVELS.length - 1) {
      events.levelUp = true;
      state.status = 'won-level';
      state.food = null;
    } else {
      state.food = spawnFood(state);
      if (!state.food) state.status = 'over'; // filled the board — a perfect game
    }
  }
  return events;
}

function die(state, events) {
  state.status = 'over';
  events.died = true;
  return events;
}

/** Move on to the next level after a 'won-level' pause. */
export function nextLevel(state) {
  if (state.status !== 'won-level') return state;
  return loadLevel(state, state.level + 1);
}

/** Toggle pause between running and paused. */
export function togglePause(state) {
  if (state.status === 'running') state.status = 'paused';
  else if (state.status === 'paused') state.status = 'running';
  return state.status;
}
