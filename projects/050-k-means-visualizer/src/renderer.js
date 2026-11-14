/**
 * Canvas rendering. Points live in [0,1]²; this module maps them to pixels.
 * Only runs in the browser, but `palette` and `voronoiCells` are pure helpers.
 */
import { nearest } from './kmeans.js';

/** Colour-blind-friendly categorical palette (Okabe–Ito + extras). */
export const PALETTE = [
  '#0072B2', '#E69F00', '#009E73', '#CC79A7', '#D55E00',
  '#56B4E9', '#F0E442', '#7F3C8D', '#11A579', '#E73F74',
];
export const colorFor = (j) => (j < 0 ? '#9aa0a6' : PALETTE[j % PALETTE.length]);

/**
 * Sample the Voronoi diagram of the centroids on a coarse grid.
 * Returns a cols×rows array of nearest-centroid indices.
 */
export function voronoiCells(centroids, cols, rows) {
  const cells = new Int16Array(cols * rows);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      cells[r * cols + c] = nearest({ x: (c + 0.5) / cols, y: (r + 0.5) / rows }, centroids);
    }
  }
  return cells;
}

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.showRegions = true;
    this.showLinks = false;
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const { width } = this.canvas.getBoundingClientRect();
    this.size = width;
    this.canvas.width = Math.round(width * dpr);
    this.canvas.height = Math.round(width * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  /** Convert a mouse event to unit-square coordinates. */
  toUnit(evt) {
    const rect = this.canvas.getBoundingClientRect();
    return { x: (evt.clientX - rect.left) / rect.width, y: (evt.clientY - rect.top) / rect.height };
  }

  draw(points, event, { prevCentroids = null } = {}) {
    const { ctx, size: S } = this;
    ctx.clearRect(0, 0, S, S);
    const centroids = event?.centroids ?? [];
    const assignments = event?.assignments ?? [];

    // 1. Voronoi regions — the decision boundary of the current centroids.
    if (this.showRegions && centroids.length) {
      const res = 4; // px per cell
      const n = Math.ceil(S / res);
      const cells = voronoiCells(centroids, n, n);
      ctx.globalAlpha = 0.12;
      for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
          ctx.fillStyle = colorFor(cells[r * n + c]);
          ctx.fillRect(c * res, r * res, res, res);
        }
      }
      ctx.globalAlpha = 1;
    }

    // 2. Point → centroid links.
    if (this.showLinks && centroids.length) {
      ctx.lineWidth = 0.6;
      ctx.globalAlpha = 0.35;
      points.forEach((p, i) => {
        const j = assignments[i];
        if (j < 0 || j === undefined) return;
        ctx.strokeStyle = colorFor(j);
        ctx.beginPath();
        ctx.moveTo(p.x * S, p.y * S);
        ctx.lineTo(centroids[j].x * S, centroids[j].y * S);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    // 3. Data points.
    points.forEach((p, i) => {
      ctx.fillStyle = colorFor(assignments[i] ?? -1);
      ctx.beginPath();
      ctx.arc(p.x * S, p.y * S, 3.2, 0, Math.PI * 2);
      ctx.fill();
    });

    // 4. Centroid trails (where they moved from in the last update).
    if (prevCentroids && event?.type === 'update') {
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 1.5;
      centroids.forEach((c, j) => {
        const p = prevCentroids[j];
        if (!p) return;
        ctx.strokeStyle = colorFor(j);
        ctx.beginPath();
        ctx.moveTo(p.x * S, p.y * S);
        ctx.lineTo(c.x * S, c.y * S);
        ctx.stroke();
      });
      ctx.setLineDash([]);
    }

    // 5. Centroids as outlined crosses.
    centroids.forEach((c, j) => {
      const x = c.x * S;
      const y = c.y * S;
      ctx.lineWidth = 5;
      ctx.strokeStyle = '#fff';
      cross(ctx, x, y, 9);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = colorFor(j);
      cross(ctx, x, y, 9);
    });
  }
}

function cross(ctx, x, y, r) {
  ctx.beginPath();
  ctx.moveTo(x - r, y - r); ctx.lineTo(x + r, y + r);
  ctx.moveTo(x + r, y - r); ctx.lineTo(x - r, y + r);
  ctx.stroke();
}

/** Tiny line chart for the elbow curve. */
export function drawElbow(canvas, curve, chosenK, elbowK) {
  const dpr = window.devicePixelRatio || 1;
  const { width, height } = canvas.getBoundingClientRect();
  canvas.width = width * dpr; canvas.height = height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  if (!curve.length) return;
  const pad = { l: 34, r: 10, t: 10, b: 22 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const maxI = Math.max(...curve.map((p) => p.inertia)) || 1;
  const kMin = curve[0].k; const kMax = curve[curve.length - 1].k;
  const X = (k) => pad.l + (kMax === kMin ? w / 2 : ((k - kMin) / (kMax - kMin)) * w);
  const Y = (v) => pad.t + h - (v / maxI) * h;
  const css = getComputedStyle(document.documentElement);
  const fg = css.getPropertyValue('--muted').trim() || '#666';
  const accent = css.getPropertyValue('--accent').trim() || '#0072B2';

  ctx.strokeStyle = fg; ctx.fillStyle = fg; ctx.lineWidth = 1;
  ctx.font = '11px system-ui, sans-serif';
  ctx.beginPath(); ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, pad.t + h); ctx.lineTo(pad.l + w, pad.t + h); ctx.stroke();
  ctx.textAlign = 'center';
  curve.forEach((p) => ctx.fillText(String(p.k), X(p.k), height - 6));
  ctx.save(); ctx.translate(10, pad.t + h / 2); ctx.rotate(-Math.PI / 2); ctx.fillText('inertia', 0, 0); ctx.restore();

  ctx.strokeStyle = accent; ctx.lineWidth = 2;
  ctx.beginPath();
  curve.forEach((p, i) => (i ? ctx.lineTo(X(p.k), Y(p.inertia)) : ctx.moveTo(X(p.k), Y(p.inertia))));
  ctx.stroke();
  curve.forEach((p) => {
    ctx.fillStyle = p.k === elbowK ? '#D55E00' : accent;
    ctx.beginPath(); ctx.arc(X(p.k), Y(p.inertia), p.k === chosenK ? 5 : 3, 0, Math.PI * 2); ctx.fill();
  });
}
