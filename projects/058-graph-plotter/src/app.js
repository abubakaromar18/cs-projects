/**
 * App wiring: DOM, input handling and the render loop.
 *
 * State lives in two places:
 *   - `viewport` (immutable Viewport, replaced on every pan/zoom)
 *   - `fns`      (the list of user expressions with their compiled closures)
 *
 * Rendering is scheduled with requestAnimationFrame and coalesced, so a burst
 * of wheel events produces at most one redraw per frame.
 */

import { tryCompile } from './compiler.js';
import { Viewport } from './viewport.js';
import { sample } from './sampler.js';
import { render, THEMES } from './renderer.js';
import { formatTick, niceStep } from './ticks.js';

const PALETTE = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#db2777'];
const DEFAULT_EXPRS = ['sin(x)', 'x^2/4 - 2', 'tan(x)'];

const canvas = document.getElementById('plot');
const ctx = canvas.getContext('2d');
const list = document.getElementById('fn-list');
const readout = document.getElementById('readout');
const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');

let viewport = Viewport.centered(800, 600, 10);
let fns = [];
let hoverX = null;
let frameRequested = false;
let nextColor = 0;

// ---------- function list ----------

function addFunction(expr = '') {
  const item = { expr, color: PALETTE[nextColor++ % PALETTE.length], fn: null, error: null };
  fns.push(item);

  const row = document.createElement('li');
  row.className = 'fn-row';
  row.innerHTML = `
    <span class="swatch" style="background:${item.color}"></span>
    <label class="fn-label">y =
      <input type="text" spellcheck="false" autocomplete="off" aria-label="Function expression">
    </label>
    <button class="remove" title="Remove" aria-label="Remove function">×</button>
    <div class="error" role="status"></div>`;
  const input = row.querySelector('input');
  const errorEl = row.querySelector('.error');
  input.value = expr;

  const update = () => {
    item.expr = input.value;
    const result = item.expr.trim() === '' ? { ok: false, error: null } : tryCompile(item.expr);
    item.fn = result.ok ? result.fn : null;
    item.error = result.ok ? null : result.error;
    errorEl.textContent = item.error ?? '';
    row.classList.toggle('invalid', Boolean(item.error));
    saveToHash();
    requestRender();
  };
  input.addEventListener('input', update);
  row.querySelector('.remove').addEventListener('click', () => {
    fns = fns.filter((f) => f !== item);
    row.remove();
    saveToHash();
    requestRender();
  });

  list.appendChild(row);
  update();
  return input;
}

// Persist expressions in the URL hash so a plot can be shared as a link.
function saveToHash() {
  const exprs = fns.map((f) => f.expr).filter((e) => e.trim());
  history.replaceState(null, '', '#' + exprs.map(encodeURIComponent).join(';'));
}

function loadFromHash() {
  const h = location.hash.slice(1);
  if (!h) return null;
  try {
    return h.split(';').map(decodeURIComponent).filter(Boolean);
  } catch {
    return null;
  }
}

// ---------- rendering ----------

function requestRender() {
  if (frameRequested) return;
  frameRequested = true;
  requestAnimationFrame(() => {
    frameRequested = false;
    draw();
  });
}

function draw() {
  const curves = fns
    .filter((f) => f.fn)
    .map((f) => ({ color: f.color, segments: sample(f.fn, viewport) }));

  let hover = null;
  if (hoverX !== null) {
    const points = fns.filter((f) => f.fn).map((f) => ({ y: f.fn(hoverX), color: f.color }));
    hover = { x: hoverX, points };
    // Show ~3 more digits than the visible tick spacing; values smaller than
    // that resolution are displayed as 0 rather than as float noise (2e-16).
    const fmt = (v, span) => {
      const step = niceStep(span, 1000);
      return Math.abs(v) < step / 2 ? '0' : formatTick(v, step);
    };
    readout.innerHTML = `x = ${fmt(hoverX, viewport.xSpan)}` + points
      .map((p) => ` &nbsp;<span style="color:${p.color}">y = ${Number.isFinite(p.y) ? fmt(p.y, viewport.ySpan) : 'undefined'}</span>`)
      .join('');
  } else {
    readout.textContent = 'Drag to pan · scroll to zoom (Shift/Alt = one axis) · double-click to reset';
  }

  const dpr = window.devicePixelRatio || 1;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  render(ctx, viewport, curves, { theme: darkQuery.matches ? THEMES.dark : THEMES.light, hover });
}

function resize() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  viewport = viewport.resize(rect.width, rect.height);
  requestRender();
}

// ---------- input: pan, zoom, pinch ----------

const pointers = new Map(); // pointerId -> {x, y}
let pinchDist = null;

const localPoint = (e) => {
  const r = canvas.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
};

canvas.addEventListener('pointerdown', (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, localPoint(e));
  canvas.classList.add('dragging');
});

canvas.addEventListener('pointermove', (e) => {
  const p = localPoint(e);
  const prev = pointers.get(e.pointerId);

  if (prev && pointers.size === 1) {
    viewport = viewport.panByPixels(p.x - prev.x, p.y - prev.y);
  } else if (prev && pointers.size === 2) {
    // Pinch: zoom about the midpoint by the ratio of finger distances.
    pointers.set(e.pointerId, p);
    const [a, b] = [...pointers.values()];
    const dist = Math.hypot(a.x - b.x, a.y - b.y);
    if (pinchDist) viewport = viewport.zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, pinchDist / dist);
    pinchDist = dist;
  }
  if (prev) pointers.set(e.pointerId, p);

  hoverX = e.pointerType === 'mouse' ? viewport.toWorldX(p.x) : null;
  requestRender();
});

const endPointer = (e) => {
  pointers.delete(e.pointerId);
  pinchDist = null;
  if (pointers.size === 0) canvas.classList.remove('dragging');
};
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
canvas.addEventListener('pointerleave', () => {
  hoverX = null;
  requestRender();
});

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const { x, y } = localPoint(e);
  // Exponential mapping: equal wheel distance = equal zoom ratio.
  const k = Math.exp(e.deltaY * 0.0015);
  viewport = viewport.zoomAt(x, y, e.altKey ? 1 : k, e.shiftKey ? 1 : k);
  hoverX = viewport.toWorldX(x);
  requestRender();
}, { passive: false });

function resetView() {
  viewport = Viewport.centered(viewport.width, viewport.height, 10);
  requestRender();
}
canvas.addEventListener('dblclick', resetView);

canvas.addEventListener('keydown', (e) => {
  const step = 40;
  const cx = viewport.width / 2;
  const cy = viewport.height / 2;
  const actions = {
    ArrowLeft: () => viewport.panByPixels(step, 0),
    ArrowRight: () => viewport.panByPixels(-step, 0),
    ArrowUp: () => viewport.panByPixels(0, step),
    ArrowDown: () => viewport.panByPixels(0, -step),
    '+': () => viewport.zoomAt(cx, cy, 0.8),
    '=': () => viewport.zoomAt(cx, cy, 0.8),
    '-': () => viewport.zoomAt(cx, cy, 1.25),
    '0': () => Viewport.centered(viewport.width, viewport.height, 10),
  };
  if (actions[e.key]) {
    e.preventDefault();
    viewport = actions[e.key]();
    requestRender();
  }
});

// ---------- toolbar ----------

document.getElementById('add').addEventListener('click', () => addFunction('').focus());
document.getElementById('zoom-in').addEventListener('click', () => {
  viewport = viewport.zoomAt(viewport.width / 2, viewport.height / 2, 0.8);
  requestRender();
});
document.getElementById('zoom-out').addEventListener('click', () => {
  viewport = viewport.zoomAt(viewport.width / 2, viewport.height / 2, 1.25);
  requestRender();
});
document.getElementById('reset').addEventListener('click', resetView);

darkQuery.addEventListener('change', requestRender);
new ResizeObserver(resize).observe(canvas);

(loadFromHash() ?? DEFAULT_EXPRS).forEach((e) => addFunction(e));
resize();
