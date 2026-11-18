/**
 * Canvas renderer: grid, axes, tick labels and function curves.
 *
 * Pure drawing code — it receives a 2D context, a viewport and a list of
 * already-sampled curves, and has no knowledge of the DOM or input handling.
 */

import { ticks, formatTick } from './ticks.js';

export const THEMES = {
  light: { bg: '#ffffff', minor: '#eef0f4', major: '#d5d9e2', axis: '#3b4252', label: '#5b6475' },
  dark: { bg: '#15181e', minor: '#1f232b', major: '#2d333d', axis: '#c7ccd6', label: '#8b93a3' },
};

export function render(ctx, vp, curves, { theme = THEMES.light, hover = null } = {}) {
  const { width, height } = vp;
  ctx.save();
  ctx.fillStyle = theme.bg;
  ctx.fillRect(0, 0, width, height);

  const tx = ticks(vp.xMin, vp.xMax, Math.max(4, Math.round(width / 90)));
  const ty = ticks(vp.yMin, vp.yMax, Math.max(4, Math.round(height / 70)));

  drawGrid(ctx, vp, tx, ty, theme);
  drawAxes(ctx, vp, tx, ty, theme);

  for (const curve of curves) drawCurve(ctx, vp, curve);
  if (hover) drawHover(ctx, vp, hover, theme);
  ctx.restore();
}

function drawGrid(ctx, vp, tx, ty, theme) {
  // Minor grid: 5 subdivisions of each major step.
  ctx.lineWidth = 1;
  ctx.strokeStyle = theme.minor;
  ctx.beginPath();
  gridLines(ctx, vp, tx.step / 5, ty.step / 5);
  ctx.stroke();

  ctx.strokeStyle = theme.major;
  ctx.beginPath();
  gridLines(ctx, vp, tx.step, ty.step);
  ctx.stroke();
}

function gridLines(ctx, vp, sxStep, syStep) {
  for (let i = Math.ceil(vp.xMin / sxStep); i * sxStep <= vp.xMax; i++) {
    const sx = Math.round(vp.toScreenX(i * sxStep)) + 0.5; // +0.5 = crisp 1px lines
    ctx.moveTo(sx, 0);
    ctx.lineTo(sx, vp.height);
  }
  for (let i = Math.ceil(vp.yMin / syStep); i * syStep <= vp.yMax; i++) {
    const sy = Math.round(vp.toScreenY(i * syStep)) + 0.5;
    ctx.moveTo(0, sy);
    ctx.lineTo(vp.width, sy);
  }
}

function drawAxes(ctx, vp, tx, ty, theme) {
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  // When an axis is off-screen, pin its labels to the nearest edge.
  const ax = clamp(vp.toScreenY(0), 0, vp.height);
  const ay = clamp(vp.toScreenX(0), 0, vp.width);

  ctx.strokeStyle = theme.axis;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(0, Math.round(ax) + 0.5);
  ctx.lineTo(vp.width, Math.round(ax) + 0.5);
  ctx.moveTo(Math.round(ay) + 0.5, 0);
  ctx.lineTo(Math.round(ay) + 0.5, vp.height);
  ctx.stroke();

  ctx.fillStyle = theme.label;
  ctx.font = '12px system-ui, sans-serif';

  ctx.textAlign = 'center';
  const below = ax < vp.height - 18;
  ctx.textBaseline = below ? 'top' : 'bottom';
  for (const v of tx.values) {
    if (v === 0) continue;
    ctx.fillText(formatTick(v, tx.step), vp.toScreenX(v), below ? ax + 4 : ax - 4);
  }

  const right = ay < vp.width - 50;
  ctx.textAlign = right ? 'left' : 'right';
  ctx.textBaseline = 'middle';
  for (const v of ty.values) {
    if (v === 0) continue;
    ctx.fillText(formatTick(v, ty.step), right ? ay + 5 : ay - 5, vp.toScreenY(v));
  }
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillText('0', ay + 5, ax + 4);
}

function drawCurve(ctx, vp, { segments, color, width = 2.25 }) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.beginPath();
  // Clamp far off-screen points: canvas implementations misbehave with huge coordinates.
  const lim = 1e5;
  const clampY = (y) => Math.max(-lim, Math.min(lim, y));
  for (const seg of segments) {
    seg.forEach(([x, y], i) => {
      const sx = vp.toScreenX(x);
      const sy = clampY(vp.toScreenY(y));
      if (i === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    });
    if (seg.length === 1) {
      const [x, y] = seg[0];
      ctx.moveTo(vp.toScreenX(x) + 0.01, clampY(vp.toScreenY(y)));
      ctx.lineTo(vp.toScreenX(x), clampY(vp.toScreenY(y)));
    }
  }
  ctx.stroke();
}

function drawHover(ctx, vp, { x, points }, theme) {
  const sx = vp.toScreenX(x);
  ctx.strokeStyle = theme.major;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(sx, 0);
  ctx.lineTo(sx, vp.height);
  ctx.stroke();
  ctx.setLineDash([]);
  for (const { y, color } of points) {
    if (!Number.isFinite(y)) continue;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(sx, vp.toScreenY(y), 4.5, 0, Math.PI * 2);
    ctx.fill();
  }
}
