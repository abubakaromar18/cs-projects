// Canvas renderer. Reads game state, draws it; never mutates state.

import { currentLevel } from './game.js';

const COLORS = {
  bg: '#0f1720',
  grid: '#16212c',
  wall: '#4b5b6b',
  head: '#7ee787',
  body: '#3fb950',
  food: '#ff7b72',
  text: '#e6edf3',
  dim: 'rgba(15, 23, 32, 0.72)',
};

export class Renderer {
  /** @param {HTMLCanvasElement} canvas */
  constructor(canvas, cols, rows) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.cols = cols;
    this.rows = rows;
    this.resize();
  }

  /** Size the backing store for crisp pixels on high-DPI screens. */
  resize() {
    const dpr = window.devicePixelRatio || 1;
    const cssSize = this.canvas.clientWidth || 480;
    this.canvas.width = Math.round(cssSize * dpr);
    this.canvas.height = Math.round(cssSize * (this.rows / this.cols) * dpr);
    this.cell = this.canvas.width / this.cols;
  }

  draw(state, now = performance.now()) {
    const { ctx, cell } = this;
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Subtle checkerboard so movement is easy to read.
    ctx.fillStyle = COLORS.grid;
    for (let y = 0; y < this.rows; y++)
      for (let x = (y % 2); x < this.cols; x += 2) ctx.fillRect(x * cell, y * cell, cell, cell);

    ctx.fillStyle = COLORS.wall;
    for (const k of state.walls) {
      const [x, y] = k.split(',').map(Number);
      ctx.fillRect(x * cell + 1, y * cell + 1, cell - 2, cell - 2);
    }

    if (state.food) {
      // Gentle pulse on the food.
      const r = cell * (0.32 + 0.05 * Math.sin(now / 150));
      ctx.fillStyle = COLORS.food;
      ctx.beginPath();
      ctx.arc((state.food.x + 0.5) * cell, (state.food.y + 0.5) * cell, r, 0, Math.PI * 2);
      ctx.fill();
    }

    state.snake.forEach((s, i) => {
      ctx.fillStyle = i === 0 ? COLORS.head : COLORS.body;
      const inset = i === 0 ? 1 : 2;
      roundRect(ctx, s.x * cell + inset, s.y * cell + inset, cell - inset * 2, cell - inset * 2, cell * 0.25);
    });

    const overlay = {
      ready: ['Level ' + (state.level + 1) + ': ' + currentLevel(state).name, 'Press an arrow key or WASD to start'],
      paused: ['Paused', 'Press P or Space to resume'],
      'won-level': ['Level complete!', 'Press Enter for the next level'],
      over: ['Game over', 'Press Enter to play again'],
    }[state.status];
    if (overlay) this.banner(...overlay);
  }

  banner(title, sub) {
    const { ctx, canvas } = this;
    ctx.fillStyle = COLORS.dim;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = `600 ${Math.round(canvas.width / 16)}px system-ui, sans-serif`;
    ctx.fillText(title, canvas.width / 2, canvas.height / 2 - canvas.width / 28);
    ctx.font = `${Math.round(canvas.width / 32)}px system-ui, sans-serif`;
    ctx.fillText(sub, canvas.width / 2, canvas.height / 2 + canvas.width / 24);
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
  ctx.fill();
}
