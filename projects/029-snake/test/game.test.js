import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, turn, step, spawnFood, nextLevel, togglePause, pointsFor, key } from '../src/game.js';
import { LEVELS } from '../src/levels.js';

const fixedRng = () => 0; // always pick the first free cell

/** Build a game with the food placed at an exact spot. */
function gameWithFood(food, opts = {}) {
  const g = createGame({ width: 10, height: 10, rng: fixedRng, ...opts });
  g.food = food;
  return g;
}

test('new game starts ready with a 3-cell snake facing right', () => {
  const g = createGame({ width: 10, height: 10, rng: fixedRng });
  assert.equal(g.status, 'ready');
  assert.equal(g.snake.length, 3);
  assert.equal(g.dir, 'right');
  assert.ok(g.food);
});

test('step does nothing until the player turns', () => {
  const g = createGame({ width: 10, height: 10, rng: fixedRng });
  const before = JSON.stringify(g.snake);
  step(g);
  assert.equal(JSON.stringify(g.snake), before);
});

test('snake moves one cell per tick in the queued direction', () => {
  const g = gameWithFood({ x: 9, y: 9 });
  const head = { ...g.snake[0] };
  turn(g, 'down');
  step(g);
  assert.deepEqual(g.snake[0], { x: head.x, y: head.y + 1 });
  assert.equal(g.snake.length, 3);
});

test('reversing direction is rejected', () => {
  const g = createGame({ width: 10, height: 10 });
  assert.equal(turn(g, 'left'), false);
  assert.equal(turn(g, 'up'), true);
  assert.equal(turn(g, 'down'), false, 'down reverses the queued up');
  assert.equal(turn(g, 'up'), false, 'duplicate is rejected');
  assert.equal(turn(g, 'nope'), false);
});

test('input queue lets two quick turns land on consecutive ticks', () => {
  const g = gameWithFood({ x: 9, y: 9 });
  const h = { ...g.snake[0] };
  turn(g, 'up');
  turn(g, 'left');
  step(g);
  step(g);
  assert.deepEqual(g.snake[0], { x: h.x - 1, y: h.y - 1 });
});

test('eating food grows the snake, scores, and respawns food', () => {
  const g = createGame({ width: 10, height: 10, rng: fixedRng });
  const h = g.snake[0];
  g.food = { x: h.x, y: h.y + 1 };
  turn(g, 'down');
  const ev = step(g);
  assert.equal(ev.ate, true);
  assert.equal(g.snake.length, 4);
  assert.equal(g.score, pointsFor(0));
  assert.ok(g.food);
  assert.ok(!g.snake.some((s) => s.x === g.food.x && s.y === g.food.y), 'food not on snake');
});

test('open-field level wraps around edges', () => {
  const g = gameWithFood({ x: 0, y: 0 });
  assert.equal(LEVELS[0].wrap, true);
  g.snake = [{ x: 9, y: 5 }, { x: 8, y: 5 }, { x: 7, y: 5 }];
  g.status = 'running';
  step(g);
  assert.deepEqual(g.snake[0], { x: 0, y: 5 });
});

test('hitting a wall ends the game', () => {
  const g = createGame({ width: 10, height: 10, rng: fixedRng, level: 1 });
  assert.ok(g.walls.has(key({ x: 9, y: 2 })));
  g.snake = [{ x: 8, y: 2 }, { x: 7, y: 2 }, { x: 6, y: 2 }];
  g.status = 'running';
  const ev = step(g);
  assert.equal(ev.died, true);
  assert.equal(g.status, 'over');
});

test('running into own body ends the game', () => {
  const g = gameWithFood({ x: 0, y: 0 });
  // Turning down puts the head on a body cell that is not the tail.
  g.snake = [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }, { x: 3, y: 6 }, { x: 4, y: 6 }, { x: 5, y: 6 }, { x: 6, y: 6 }];
  g.status = 'running';
  turn(g, 'down');
  const ev = step(g);
  assert.equal(ev.died, true);
});

test('moving into the cell the tail is leaving is allowed', () => {
  const g = gameWithFood({ x: 0, y: 0 });
  // 2x2 loop: head chases tail.
  g.snake = [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 4, y: 6 }, { x: 4, y: 5 }];
  g.dir = 'up';
  g.status = 'running';
  turn(g, 'left');
  const ev = step(g);
  assert.equal(ev.died, false);
  assert.deepEqual(g.snake[0], { x: 4, y: 5 });
});

test('eating enough food completes the level and nextLevel loads the next one', () => {
  const g = createGame({ width: 24, height: 24, rng: fixedRng });
  g.foodEatenThisLevel = LEVELS[0].foodToAdvance - 1;
  const h = g.snake[0];
  g.food = { x: h.x + 1, y: h.y };
  turn(g, 'up'); // start the game...
  g.queue = []; // ...but keep heading right
  const ev = step(g);
  assert.equal(ev.levelUp, true);
  assert.equal(g.status, 'won-level');
  const score = g.score;
  nextLevel(g);
  assert.equal(g.level, 1);
  assert.equal(g.status, 'ready');
  assert.equal(g.score, score, 'score carries over');
  assert.equal(g.snake.length, 3);
});

test('every level starts with the snake and food off the walls', () => {
  for (let i = 0; i < LEVELS.length; i++) {
    for (const size of [16, 24, 32]) {
      const g = createGame({ width: size, height: size, level: i });
      for (const s of g.snake) assert.ok(!g.walls.has(key(s)), `level ${i} size ${size}: snake in wall`);
      assert.ok(!g.walls.has(key(g.food)), `level ${i}: food in wall`);
      // The first few moves to the right must be safe.
      turn(g, 'up');
      g.queue = [];
      step(g);
      assert.notEqual(g.status, 'over', `level ${i} size ${size}: immediate death`);
    }
  }
});

test('spawnFood returns null when the board is full', () => {
  const g = createGame({ width: 2, height: 2, rng: fixedRng });
  g.walls = new Set();
  g.snake = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }];
  assert.equal(spawnFood(g), null);
});

test('spawnFood is uniform over free cells using the injected RNG', () => {
  const g = createGame({ width: 3, height: 1, rng: () => 0.99 });
  g.walls = new Set();
  g.snake = [{ x: 0, y: 0 }];
  assert.deepEqual(spawnFood(g), { x: 2, y: 0 });
});

test('pause toggles only while running', () => {
  const g = createGame({ width: 10, height: 10 });
  assert.equal(togglePause(g), 'ready');
  turn(g, 'up');
  assert.equal(togglePause(g), 'paused');
  const snap = JSON.stringify(g.snake);
  step(g);
  assert.equal(JSON.stringify(g.snake), snap, 'no movement while paused');
  assert.equal(togglePause(g), 'running');
});

test('later levels are faster and worth more points', () => {
  for (let i = 1; i < LEVELS.length; i++) {
    assert.ok(LEVELS[i].tickMs < LEVELS[i - 1].tickMs);
    assert.ok(pointsFor(i) > pointsFor(i - 1));
  }
});
