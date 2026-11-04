// Browser entry point: wires input, the fixed-timestep loop, rendering and
// the high-score table together.

import { createGame, turn, step, nextLevel, togglePause, currentLevel } from './game.js';
import { HighScores, memoryStorage } from './highscores.js';
import { Renderer } from './renderer.js';

const COLS = 24;
const ROWS = 24;

const $ = (sel) => document.querySelector(sel);
const canvas = $('#board');
const scoreEl = $('#score');
const bestEl = $('#best');
const levelEl = $('#level');
const tableEl = $('#scores');

function safeStorage() {
  try {
    const t = '__snake_test__';
    localStorage.setItem(t, t);
    localStorage.removeItem(t);
    return localStorage;
  } catch {
    return memoryStorage();
  }
}

const scores = new HighScores(safeStorage());
const renderer = new Renderer(canvas, COLS, ROWS);
let game = createGame({ width: COLS, height: ROWS });
let recorded = false;

const KEYMAP = {
  ArrowUp: 'up', KeyW: 'up',
  ArrowDown: 'down', KeyS: 'down',
  ArrowLeft: 'left', KeyA: 'left',
  ArrowRight: 'right', KeyD: 'right',
};

window.addEventListener('keydown', (e) => {
  const dir = KEYMAP[e.code];
  if (dir) {
    e.preventDefault();
    if (game.status === 'ready' || game.status === 'running') turn(game, dir);
    return;
  }
  if (e.code === 'KeyP' || e.code === 'Space') {
    e.preventDefault();
    togglePause(game);
  } else if (e.code === 'Enter') {
    if (game.status === 'won-level') nextLevel(game);
    else if (game.status === 'over') restart();
  }
});

// Swipe controls for touch screens.
let touchStart = null;
canvas.addEventListener('touchstart', (e) => {
  const t = e.changedTouches[0];
  touchStart = { x: t.clientX, y: t.clientY };
}, { passive: true });
canvas.addEventListener('touchend', (e) => {
  if (!touchStart) return;
  const t = e.changedTouches[0];
  const dx = t.clientX - touchStart.x;
  const dy = t.clientY - touchStart.y;
  touchStart = null;
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 20) {
    // A tap advances menus.
    if (game.status === 'won-level') nextLevel(game);
    else if (game.status === 'over') restart();
    else togglePause(game);
    return;
  }
  turn(game, Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'));
});

function restart() {
  game = createGame({ width: COLS, height: ROWS });
  recorded = false;
}

function onGameOver() {
  if (recorded) return;
  recorded = true;
  if (scores.qualifies(game.score)) {
    const name = (window.prompt('New high score! Your name:', 'Player') ?? 'Player').trim();
    scores.add({ name, score: game.score, level: game.level });
  }
  renderScores();
}

function renderScores() {
  const rows = scores.list();
  tableEl.innerHTML = rows.length
    ? rows.map((r, i) => `<li><span>${i + 1}. ${escapeHtml(r.name)}</span><span>${r.score} · L${r.level + 1}</span></li>`).join('')
    : '<li class="empty">No scores yet</li>';
  bestEl.textContent = String(scores.best());
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// Fixed-timestep loop: logic advances at the level's tick rate regardless of
// display refresh rate; rendering happens every animation frame.
let last = performance.now();
let acc = 0;
function frame(now) {
  acc += Math.min(now - last, 250); // clamp so a background tab doesn't fast-forward
  last = now;
  const tick = currentLevel(game).tickMs;
  while (acc >= tick) {
    acc -= tick;
    const ev = step(game);
    if (ev.died || game.status === 'over') onGameOver();
  }
  scoreEl.textContent = String(game.score);
  levelEl.textContent = `${game.level + 1} · ${currentLevel(game).name}`;
  renderer.draw(game, now);
  requestAnimationFrame(frame);
}

window.addEventListener('resize', () => renderer.resize());
$('#clear').addEventListener('click', () => { scores.clear(); renderScores(); });
renderScores();
requestAnimationFrame(frame);
