/**
 * DOM wiring: connects the pure timer/stats modules to the page.
 * All business logic lives in timer.js and stats.js; this file only renders
 * state and translates user input into timer commands.
 */
import { PomodoroTimer, Phase, Status, formatTime } from './timer.js';
import { SessionLog, MemoryStorage, summarize, lastNDays } from './stats.js';
import { playAlert, unlockAudio } from './sound.js';

const SETTINGS_KEY = 'pomodoro.settings.v1';
const PHASE_LABEL = { work: 'Focus', shortBreak: 'Short break', longBreak: 'Long break' };

// ── storage (localStorage may throw in private mode or sandboxes) ─────────
function pickStorage() {
  try {
    const probe = '__pomodoro_probe__';
    localStorage.setItem(probe, '1');
    localStorage.removeItem(probe);
    return localStorage;
  } catch {
    return new MemoryStorage();
  }
}
const storage = pickStorage();

function loadPrefs() {
  try { return JSON.parse(storage.getItem(SETTINGS_KEY)) ?? {}; } catch { return {}; }
}
function savePrefs(prefs) {
  try { storage.setItem(SETTINGS_KEY, JSON.stringify(prefs)); } catch { /* ignore */ }
}

const prefs = { volume: 0.4, ...loadPrefs() };
const timer = new PomodoroTimer({ settings: prefs });
const log = new SessionLog(storage);

// ── element refs ──────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const el = {
  time: $('#time'), cycle: $('#cycle'), toggle: $('#toggle'),
  reset: $('#reset'), skip: $('#skip'), ring: $('.ring-progress'),
  tabs: document.querySelectorAll('[data-tab]'), form: $('#settings-form'),
  chart: $('#chart'), today: $('#stat-today'), focus: $('#stat-focus'),
  streak: $('#stat-streak'), total: $('#stat-total'),
};

const CIRCUMFERENCE = 2 * Math.PI * 54;
el.ring.style.strokeDasharray = String(CIRCUMFERENCE);

// ── rendering ─────────────────────────────────────────────────────────────
function renderTimer() {
  const snap = timer.snapshot();
  const time = formatTime(snap.remaining);
  el.time.textContent = time;
  el.ring.style.strokeDashoffset = String(CIRCUMFERENCE * snap.progress);
  document.body.dataset.phase = snap.phase;
  el.toggle.textContent = snap.status === Status.RUNNING ? 'Pause'
    : snap.status === Status.PAUSED ? 'Resume' : 'Start';
  el.tabs.forEach((t) => t.classList.toggle('active', t.dataset.tab === snap.phase));

  const { longBreakInterval } = timer.settings;
  el.cycle.textContent = snap.phase === Phase.WORK
    ? `Session ${(snap.completedWork % longBreakInterval) + 1} of ${longBreakInterval}`
    : PHASE_LABEL[snap.phase];
  document.title = `${time} · ${PHASE_LABEL[snap.phase]}`;
}

function renderStats() {
  const s = summarize(log.sessions);
  el.today.textContent = s.todaySessions;
  el.focus.textContent = s.todayFocusMinutes >= 60
    ? `${Math.floor(s.todayFocusMinutes / 60)}h ${s.todayFocusMinutes % 60}m`
    : `${s.todayFocusMinutes}m`;
  el.streak.textContent = s.streak;
  el.total.textContent = s.totalSessions;

  const days = lastNDays(log.sessions, 7);
  const max = Math.max(1, ...days.map((d) => d.sessions));
  el.chart.replaceChildren(...days.map((d) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.title = `${d.day}: ${d.sessions} session(s)`;
    const fill = document.createElement('div');
    fill.style.height = `${(d.sessions / max) * 80}%`;
    const label = document.createElement('span');
    label.textContent = new Date(`${d.day}T12:00`).toLocaleDateString(undefined, { weekday: 'short' });
    bar.append(fill, label);
    return bar;
  }));
}

function fillSettingsForm() {
  for (const [key, value] of Object.entries({ ...timer.settings, volume: prefs.volume })) {
    const input = el.form.elements[key];
    if (!input) continue;
    if (input.type === 'checkbox') input.checked = value;
    else input.value = value;
  }
}

// ── events ────────────────────────────────────────────────────────────────
timer.on('change', renderTimer);
timer.on('tick', renderTimer);
timer.on('complete', ({ phase, duration, at }) => {
  log.add({ phase, duration, at });
  renderStats();
  playAlert(phase === Phase.WORK ? 'workDone' : 'breakDone', prefs.volume);
  notify(phase);
});

function notify(phase) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const body = phase === Phase.WORK ? 'Nice work — time for a break.' : 'Break over — back to focus.';
  try { new Notification('Pomodoro', { body }); } catch { /* ignore */ }
}

el.toggle.addEventListener('click', () => {
  unlockAudio();
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {});
  }
  timer.toggle();
});
el.reset.addEventListener('click', () => timer.reset());
el.skip.addEventListener('click', () => timer.skip());

el.form.addEventListener('change', () => {
  const f = el.form.elements;
  timer.updateSettings({
    workMinutes: f.workMinutes.value,
    shortBreakMinutes: f.shortBreakMinutes.value,
    longBreakMinutes: f.longBreakMinutes.value,
    longBreakInterval: f.longBreakInterval.value,
    autoStartNext: f.autoStartNext.checked,
  });
  prefs.volume = Number(f.volume.value);
  Object.assign(prefs, timer.settings);
  savePrefs(prefs);
  fillSettingsForm(); // show clamped values
});

$('#test-sound').addEventListener('click', () => { unlockAudio(); playAlert('workDone', prefs.volume); });
$('#clear-stats').addEventListener('click', () => {
  if (confirm('Delete all recorded sessions?')) { log.clear(); renderStats(); }
});

document.addEventListener('keydown', (e) => {
  if (e.target.closest('input, textarea, select') || e.metaKey || e.ctrlKey) return;
  if (e.code === 'Space') { e.preventDefault(); unlockAudio(); timer.toggle(); }
  else if (e.key === 'r' || e.key === 'R') timer.reset();
  else if (e.key === 's' || e.key === 'S') timer.skip();
});

// Timer accuracy comes from wall-clock timestamps, so a coarse interval is fine;
// it also keeps working (throttled) when the tab is in the background.
setInterval(() => timer.tick(), 250);

fillSettingsForm();
renderTimer();
renderStats();
