/**
 * Browser entry point: wires the simulation, renderer and UI controls.
 */
import { ParticleSystem } from './system.js';
import { Renderer } from './renderer.js';
import { attractor, vortex } from './forces.js';
import { PATTERN_NAMES } from './fireworks.js';

const canvas = document.getElementById('sky');
const ctx = canvas.getContext('2d');
const $ = (id) => document.getElementById(id);

const system = new ParticleSystem({ seed: Date.now() & 0xffff });
const renderer = new Renderer(ctx);

// ----- Sizing (handles high-DPI screens) -----
function resize() {
  const dpr = window.devicePixelRatio || 1;
  const { clientWidth: w, clientHeight: h } = canvas;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  system.resize(w, h);
}
window.addEventListener('resize', resize);
resize();

// ----- Controls -----
const patternSel = $('pattern');
for (const name of ['random', ...PATTERN_NAMES]) {
  patternSel.add(new Option(name[0].toUpperCase() + name.slice(1), name));
}
const chosenPattern = () => (patternSel.value === 'random' ? undefined : patternSel.value);

function bindRange(id, apply, fmt = (v) => v) {
  const input = $(id);
  const out = $(`${id}-out`);
  const update = () => { const v = Number(input.value); apply(v); out.textContent = fmt(v); };
  input.addEventListener('input', update);
  update();
}
bindRange('gravity', (v) => { system.findForce('gravity').g = v; });
bindRange('wind', (v) => { system.findForce('wind').strength = v; });
bindRange('drag', (v) => { system.findForce('drag').k = v; }, (v) => v.toFixed(1));
bindRange('fade', (v) => { renderer.fade = v; }, (v) => v.toFixed(2));

let autoShow = true;
$('auto').addEventListener('change', (e) => { autoShow = e.target.checked; });
$('clear').addEventListener('click', () => {
  system.clear();
  for (const f of [...system.forces]) if (f.x !== undefined) system.removeForce(f);
});
$('finale').addEventListener('click', () => {
  for (let i = 0; i < 12; i++) {
    setTimeout(() => randomLaunch(), i * 120);
  }
});

// ----- Mouse: click launches, shift-click attracts, alt-click repels, ctrl-click swirls -----
canvas.addEventListener('pointerdown', (e) => {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  if (e.shiftKey) system.addForce(attractor(x, y, 2.5e6));
  else if (e.altKey) system.addForce(attractor(x, y, -2.5e6, 40, 250));
  else if (e.ctrlKey || e.metaKey) system.addForce(vortex(x, y));
  else system.launch(x, y, { pattern: chosenPattern() });
});

function randomLaunch() {
  const w = system.width;
  const h = system.height;
  const x = w * (0.15 + 0.7 * Math.random());
  const y = h * (0.15 + 0.35 * Math.random());
  system.launch(x, y, { pattern: chosenPattern() });
}

// ----- Main loop -----
let last = performance.now();
let nextAuto = 0;
let fpsSmoothed = 60;

function frame(now) {
  const elapsed = (now - last) / 1000;
  last = now;
  fpsSmoothed += ((1 / Math.max(elapsed, 1e-3)) - fpsSmoothed) * 0.05;

  if (autoShow && now >= nextAuto) {
    randomLaunch();
    nextAuto = now + 500 + Math.random() * 900;
  }

  system.advance(elapsed);
  renderer.draw(system);
  renderer.drawForces(system);

  $('hud').textContent =
    `${system.pool.liveCount} particles · ${Math.round(fpsSmoothed)} fps · ${system.stats.explosions} bursts`;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
