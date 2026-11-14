/**
 * UI wiring: owns the data set, rebuilds the step player when parameters
 * change, and drives playback with a timer.
 */
import { DATASETS } from './datasets.js';
import { kmeansSteps, inertia } from './kmeans.js';
import { silhouette, elbowCurve, findElbow } from './metrics.js';
import { StepPlayer } from './player.js';
import { Renderer, drawElbow } from './renderer.js';

const $ = (id) => document.getElementById(id);
const els = {
  canvas: $('canvas'), status: $('status'), dataset: $('dataset'), n: $('n'), nOut: $('nOut'),
  seed: $('seed'), regen: $('regen'), k: $('k'), kOut: $('kOut'), init: $('init'),
  back: $('back'), step: $('step'), play: $('play'), finish: $('finish'), restart: $('restart'),
  speed: $('speed'), regions: $('regions'), links: $('links'),
  phase: $('phase'), iter: $('iter'), inertia: $('inertia'), sil: $('sil'),
  elbow: $('elbow'), elbowCanvas: $('elbowCanvas'), elbowNote: $('elbowNote'),
};

const state = {
  points: [],
  manualCentroids: [], // shift-click placed seeds
  player: null,
  runSeed: 1,
  timer: null,
  elbow: null,
};

const renderer = new Renderer(els.canvas);

const PHASE_TEXT = {
  init: 'Initialise',
  assign: 'Assign (E-step)',
  update: 'Update (M-step)',
  done: 'Converged',
};

function generate() {
  const name = els.dataset.value;
  const n = Number(els.n.value);
  const seed = Number(els.seed.value) || 0;
  state.points = name === 'empty' ? [] : DATASETS[name]({ n, seed, centers: Number(els.k.value) });
  state.manualCentroids = [];
  state.elbow = null;
  els.elbowNote.textContent = '';
  drawElbow(els.elbowCanvas, [], 0, 0);
  rebuild();
}

/** Create a fresh player for the current points + settings. */
function rebuild() {
  stop();
  const k = Number(els.k.value);
  if (state.points.length < k) {
    state.player = null;
    render();
    status(`Add at least ${k} points (click the canvas).`);
    return;
  }
  const manual = state.manualCentroids.length === k ? state.manualCentroids : undefined;
  const opts = { k, init: els.init.value, seed: state.runSeed, centroids: manual };
  state.player = new StepPlayer(() => kmeansSteps(state.points, opts));
  render();
  status(manual ? 'Using your hand-placed centroids.' : `Initialised with ${els.init.selectedOptions[0].text}.`);
}

function render() {
  const p = state.player;
  const ev = p?.current ?? null;
  const prev = p && p.index > 0 ? p.history[p.index - 1].centroids : null;
  const displayEv = ev ?? (state.manualCentroids.length
    ? { centroids: state.manualCentroids, assignments: [] } : null);
  renderer.draw(state.points, displayEv, { prevCentroids: prev });

  els.phase.textContent = ev ? PHASE_TEXT[ev.type] : '—';
  els.iter.textContent = ev?.iteration ?? ev?.iterations ?? 0;
  const assigned = ev && ev.assignments.every((a) => a >= 0) && ev.assignments.length > 0;
  els.inertia.textContent = assigned ? inertia(state.points, ev.centroids, ev.assignments).toFixed(4) : '—';
  els.sil.textContent = ev?.type === 'done'
    ? silhouette(state.points, ev.assignments, ev.centroids.length).toFixed(3) : '—';

  els.back.disabled = !p || p.atStart;
  els.step.disabled = !p || p.atEnd;
  els.finish.disabled = !p || p.atEnd;
  els.play.disabled = !p || p.atEnd;
  els.play.textContent = state.timer ? 'Pause' : 'Play';

  if (ev?.type === 'assign') status(`${ev.changed} point(s) changed cluster.`);
  if (ev?.type === 'update') status(`Centroids moved a total of ${ev.shift.toFixed(4)}.`);
  if (ev?.type === 'done') status(`Done after ${ev.iterations} iteration(s): ${ev.reason}.`);
}

function status(msg) { els.status.textContent = msg; }

function step() { state.player?.forward(); if (state.player?.atEnd) stop(); render(); }
function back() { stop(); state.player?.back(); render(); }

function play() {
  if (state.timer) { stop(); render(); return; }
  if (!state.player || state.player.atEnd) return;
  const tick = () => {
    step();
    if (state.timer) state.timer = setTimeout(tick, Number(els.speed.max) + Number(els.speed.min) - Number(els.speed.value));
  };
  state.timer = setTimeout(tick, 0);
  render();
}

function stop() {
  if (state.timer) clearTimeout(state.timer);
  state.timer = null;
}

// --- events ---------------------------------------------------------------

els.canvas.addEventListener('click', (e) => {
  const p = renderer.toUnit(e);
  if (e.shiftKey) {
    const k = Number(els.k.value);
    if (state.manualCentroids.length >= k) state.manualCentroids = [];
    state.manualCentroids.push(p);
    if (state.manualCentroids.length === k) rebuild();
    else { state.player = null; render(); status(`Placed ${state.manualCentroids.length}/${k} centroids.`); }
    return;
  }
  state.points.push(p);
  state.elbow = null;
  rebuild();
});

els.n.addEventListener('input', () => { els.nOut.textContent = els.n.value; });
els.k.addEventListener('input', () => {
  els.kOut.textContent = els.k.value;
  state.manualCentroids = [];
  rebuild();
  if (state.elbow) drawElbow(els.elbowCanvas, state.elbow.curve, Number(els.k.value), state.elbow.k);
});
els.init.addEventListener('change', () => { state.manualCentroids = []; rebuild(); });
els.dataset.addEventListener('change', generate);
els.regen.addEventListener('click', generate);
els.step.addEventListener('click', step);
els.back.addEventListener('click', back);
els.play.addEventListener('click', play);
els.finish.addEventListener('click', () => { stop(); state.player?.toEnd(); render(); });
els.restart.addEventListener('click', () => { state.runSeed++; state.manualCentroids = []; rebuild(); });
els.regions.addEventListener('change', () => { renderer.showRegions = els.regions.checked; render(); });
els.links.addEventListener('change', () => { renderer.showLinks = els.links.checked; render(); });

els.elbow.addEventListener('click', () => {
  if (state.points.length < 2) { els.elbowNote.textContent = 'Need more points.'; return; }
  const curve = elbowCurve(state.points, { kMin: 1, kMax: 10, restarts: 4, seed: 11 });
  const k = findElbow(curve);
  state.elbow = { curve, k };
  drawElbow(els.elbowCanvas, curve, Number(els.k.value), k);
  const bestSil = curve.filter((c) => c.k >= 2).reduce((a, b) => (b.silhouette > a.silhouette ? b : a), { silhouette: -Infinity });
  els.elbowNote.textContent = `Elbow at k = ${k} (orange). Best silhouette: k = ${bestSil.k} (${bestSil.silhouette.toFixed(3)}).`;
});

document.addEventListener('keydown', (e) => {
  if (e.target.matches('input, select')) return;
  if (e.key === 'ArrowRight') step();
  else if (e.key === 'ArrowLeft') back();
  else if (e.key === ' ') { e.preventDefault(); play(); }
  else if (e.key.toLowerCase() === 'r') els.restart.click();
});

window.addEventListener('resize', () => { renderer.resize(); render(); });

renderer.resize();
generate();
