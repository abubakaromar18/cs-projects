/**
 * DOM layer: wires the controls to a Player and renders its state as bars.
 * All sorting and playback logic lives in algorithms.js and player.js.
 */
import { ALGORITHMS } from './algorithms.js';
import { Player, generateArray, playbackRate } from './player.js';

const $ = (id) => document.getElementById(id);
const els = {
  algorithm: $('algorithm'), preset: $('preset'),
  size: $('size'), sizeOut: $('size-out'),
  speed: $('speed'), speedOut: $('speed-out'),
  sound: $('sound'),
  play: $('play'), step: $('step'), reset: $('reset'), shuffle: $('shuffle'),
  bars: $('bars'),
  stats: {
    comparisons: $('stat-comparisons'), swaps: $('stat-swaps'),
    writes: $('stat-writes'), steps: $('stat-steps'),
  },
};

let values = [];
let player = null;
let barEls = [];
let timer = null;
let audio = null;

/** Short sine blip whose pitch follows the bar height being touched. */
function beep(value) {
  if (!els.sound.checked) return;
  try {
    audio ??= new AudioContext();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.frequency.value = 200 + value * 8;
    gain.gain.setValueAtTime(0.04, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + 0.05);
    osc.connect(gain).connect(audio.destination);
    osc.start();
    osc.stop(audio.currentTime + 0.05);
  } catch {
    // Audio is optional; ignore browsers that block it.
  }
}

/** Rebuild the bar elements (only when the array length changes). */
function buildBars(n) {
  els.bars.replaceChildren();
  barEls = Array.from({ length: n }, () => {
    const div = document.createElement('div');
    div.className = 'bar';
    els.bars.append(div);
    return div;
  });
}

function render() {
  const s = player.state;
  const comparing = new Set(s.comparing);
  const swapping = new Set(s.swapping);
  const [lo, hi] = s.range ?? [-1, -2];
  for (let i = 0; i < barEls.length; i++) {
    const el = barEls[i];
    el.style.height = `${s.values[i]}%`;
    el.classList.toggle('sorted', s.done || s.sorted.has(i));
    el.classList.toggle('compare', comparing.has(i));
    el.classList.toggle('swap', swapping.has(i));
    el.classList.toggle('pivot', s.pivot === i);
    el.classList.toggle('in-range', !s.done && i >= lo && i <= hi);
  }
  for (const [key, el] of Object.entries(els.stats)) el.textContent = s.stats[key].toLocaleString();
  els.step.disabled = s.done;
  if (s.done) stop();
}

function renderComplexity() {
  const info = ALGORITHMS[els.algorithm.value];
  $('complexity-caption').textContent = info.name;
  for (const key of ['best', 'average', 'worst', 'space']) $(`cx-${key}`).textContent = info[key];
  $('cx-stable').textContent = info.stable ? 'Yes' : 'No';
}

/** Create a fresh player for the current algorithm and input. */
function load() {
  stop();
  player = new Player(ALGORITHMS[els.algorithm.value].fn, values);
  if (barEls.length !== values.length) buildBars(values.length);
  renderComplexity();
  render();
}

function newArray() {
  values = generateArray(Number(els.size.value), els.preset.value);
  load();
}

function tick() {
  const { delayMs, stepsPerTick } = playbackRate(els.speed.value);
  player.stepMany(stepsPerTick);
  const touched = player.state.swapping[0] ?? player.state.comparing[0];
  if (touched !== undefined) beep(player.state.values[touched]);
  render();
  if (!player.state.done) timer = setTimeout(tick, delayMs);
}

function play() {
  if (player.state.done) load();
  els.play.textContent = 'Pause';
  tick();
}

function stop() {
  clearTimeout(timer);
  timer = null;
  els.play.textContent = player?.state.done ? 'Replay' : 'Play';
}

const togglePlay = () => (timer ? stop() : play());

els.play.addEventListener('click', togglePlay);
els.step.addEventListener('click', () => { stop(); player.step(); render(); });
els.reset.addEventListener('click', load);
els.shuffle.addEventListener('click', newArray);
els.algorithm.addEventListener('change', load);
els.preset.addEventListener('change', newArray);
els.size.addEventListener('input', () => { els.sizeOut.value = els.size.value; newArray(); });
els.speed.addEventListener('input', () => { els.speedOut.value = els.speed.value; });

document.addEventListener('keydown', (e) => {
  if (e.target instanceof HTMLSelectElement || e.target instanceof HTMLInputElement) return;
  if (e.key === ' ') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'ArrowRight') { stop(); player.step(); render(); }
  else if (e.key === 'r' || e.key === 'R') load();
  else if (e.key === 'n' || e.key === 'N') newArray();
});

newArray();
