/**
 * Browser entry point: wires the pure core (session, passage, heatmap,
 * history) to the DOM. All test logic lives in ../core; this file only
 * handles events and rendering.
 */
import { TypingSession, type KeyStats } from "../core/session.js";
import { generatePassage } from "../core/passage.js";
import { mulberry32 } from "../core/random.js";
import { buildHeatmap, weakestKeys, avgLatency, type HeatmapMode } from "../core/heatmap.js";
import { History, type KVStore } from "../core/history.js";
import { chartGeometry, fmtDuration, fmtInt, fmtPct, modeId } from "./format.js";

type Kind = "words" | "time";

interface Settings {
  kind: Kind;
  amount: number;
  punctuation: boolean;
  numbers: boolean;
  heatMode: HeatmapMode;
  heatScope: "run" | "lifetime";
}

const $ = <T extends HTMLElement>(sel: string): T => {
  const el = document.querySelector<T>(sel);
  if (!el) throw new Error(`missing element ${sel}`);
  return el;
};

function safeStorage(): KVStore | null {
  try {
    const s = window.localStorage;
    s.getItem("probe");
    return s;
  } catch {
    return null;
  }
}

const history = new History(safeStorage());
const settings: Settings = {
  kind: "words", amount: 25, punctuation: false, numbers: false, heatMode: "errors", heatScope: "run",
};

let session: TypingSession;
let spans: HTMLSpanElement[] = [];
let lastCursor = 0;
let tick: number | undefined;
let focusKeys: string[] = [];
let lastRunStats: KeyStats = {};

const els = {
  passage: $<HTMLDivElement>("#passage"),
  wpm: $<HTMLSpanElement>("#live-wpm"),
  acc: $<HTMLSpanElement>("#live-acc"),
  timer: $<HTMLSpanElement>("#live-timer"),
  results: $<HTMLElement>("#results"),
  heatmap: $<HTMLDivElement>("#heatmap"),
  chart: (() => {
    const c = document.querySelector<SVGSVGElement>("#chart");
    if (!c) throw new Error("missing #chart");
    return c;
  })(),
  history: $<HTMLTableSectionElement>("#history-body"),
  focusNote: $<HTMLParagraphElement>("#focus-note"),
};

/* ---------- test lifecycle ---------- */

function newTest(seed = Date.now()): void {
  window.clearInterval(tick);
  tick = undefined;
  const words = settings.kind === "words" ? settings.amount : Math.max(60, settings.amount * 4);
  const text = generatePassage(
    { words, punctuation: settings.punctuation, numbers: settings.numbers, focusKeys },
    mulberry32(seed),
  );
  session = new TypingSession(text);
  renderPassage();
  els.results.hidden = true;
  els.focusNote.textContent = focusKeys.length ? `Practising weak keys: ${focusKeys.join(" ")}` : "";
  updateLive();
  els.passage.focus();
}

function finishTest(): void {
  window.clearInterval(tick);
  tick = undefined;
  const now = performance.now();
  const st = session.stats(now);
  lastRunStats = session.keyStats();
  const pb = history.add(
    {
      at: new Date().toISOString(),
      mode: modeId(settings.kind, settings.amount, settings.punctuation, settings.numbers),
      netWpm: st.netWpm, rawWpm: st.rawWpm, accuracy: st.accuracy,
      consistency: st.consistency, durationMs: st.elapsedMs,
    },
    lastRunStats,
  );
  $("#res-wpm").textContent = fmtInt(st.netWpm);
  $("#res-raw").textContent = fmtInt(st.rawWpm);
  $("#res-acc").textContent = fmtPct(st.accuracy);
  $("#res-cons").textContent = fmtPct(st.consistency);
  $("#res-time").textContent = fmtDuration(st.elapsedMs);
  $("#res-chars").textContent = `${st.correctChars}/${st.incorrectChars}/${st.correctedErrors}`;
  $("#res-pb").hidden = !pb;
  renderChart();
  renderHeatmap();
  renderHistory();
  els.results.hidden = false;
}

/* ---------- input ---------- */

function onKeyDown(e: KeyboardEvent): void {
  if (e.key === "Tab" || e.key === "Escape") {
    e.preventDefault();
    newTest();
    return;
  }
  if (session.state === "finished") return;
  const now = performance.now();

  if (e.key === "Backspace") {
    e.preventDefault();
    if (e.ctrlKey || e.altKey) session.backspaceWord(now);
    else session.backspace(now);
  } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    const wasReady = session.state === "ready";
    session.type(e.key, now);
    if (wasReady) tick = window.setInterval(onTick, 100);
  } else {
    return;
  }
  updateSpans();
  updateLive();
  if (session.isFinished()) finishTest();
}

function onTick(): void {
  const now = performance.now();
  if (settings.kind === "time" && session.elapsed(now) >= settings.amount * 1000) {
    session.finish(now);
    finishTest();
    return;
  }
  updateLive();
}

/* ---------- rendering ---------- */

function renderPassage(): void {
  els.passage.textContent = "";
  spans = [...session.target].map((ch) => {
    const s = document.createElement("span");
    s.textContent = ch;
    s.className = "ch";
    return s;
  });
  els.passage.append(...spans);
  lastCursor = 0;
  spans[0]?.classList.add("cursor");
}

/** Only touch spans between the old and new cursor positions. */
function updateSpans(): void {
  const cur = session.cursor;
  const from = Math.max(0, Math.min(lastCursor, cur) - 1);
  const to = Math.min(spans.length - 1, Math.max(lastCursor, cur));
  for (let i = from; i <= to; i++) {
    const s = spans[i]!;
    s.className = `ch ${session.charStatus(i)}${i === cur ? " cursor" : ""}`;
  }
  lastCursor = cur;
  spans[cur]?.scrollIntoView({ block: "nearest" });
}

function updateLive(): void {
  const now = performance.now();
  const st = session.stats(now);
  els.wpm.textContent = fmtInt(st.netWpm);
  els.acc.textContent = fmtPct(st.accuracy);
  if (settings.kind === "time") {
    els.timer.textContent = `${Math.max(0, Math.ceil(settings.amount - st.elapsedMs / 1000))}s`;
  } else {
    els.timer.textContent = `${session.typed.split(" ").length - (session.cursor === 0 ? 1 : 0)}/${settings.amount}`;
  }
}

function renderHeatmap(): void {
  const stats = settings.heatScope === "run" ? lastRunStats : history.lifetimeKeyStats;
  const rows = buildHeatmap(stats, { mode: settings.heatMode });
  els.heatmap.textContent = "";
  for (const row of rows) {
    const r = document.createElement("div");
    r.className = "kb-row";
    for (const cell of row) {
      const k = document.createElement("div");
      k.className = "kb-key";
      k.style.flexGrow = String(cell.key.width);
      k.textContent = cell.key.id === "space" ? "space" : cell.key.base;
      if (cell.color) k.style.background = cell.color;
      else k.classList.add("nodata");
      const lat = cell.avgLatency === null ? "–" : `${Math.round(cell.avgLatency)} ms`;
      k.title = cell.attempts
        ? `${cell.key.id}: ${cell.attempts - cell.misses}/${cell.attempts} correct, avg ${lat}`
        : `${cell.key.id}: no data`;
      r.append(k);
    }
    els.heatmap.append(r);
  }
  const weak = weakestKeys(stats);
  $("#weak-keys").textContent = weak.length ? weak.join(" ") : "none yet";
  const slow = Object.entries(stats)
    .map(([id, s]) => ({ id, lat: avgLatency(s) }))
    .filter((x): x is { id: string; lat: number } => x.lat !== null && x.id.length === 1)
    .sort((a, b) => b.lat - a.lat)
    .slice(0, 3)
    .map((x) => `${x.id} (${Math.round(x.lat)} ms)`);
  $("#slow-keys").textContent = slow.length ? slow.join(", ") : "–";
}

const SVG_NS = "http://www.w3.org/2000/svg";
function renderChart(): void {
  const W = 600, H = 160;
  // ~30 buckets regardless of test length, but never finer than 250 ms.
  const bucket = Math.max(250, session.elapsed(performance.now()) / 30);
  const g = chartGeometry(session.timeline(bucket), W, H);
  els.chart.textContent = "";
  const add = (tag: string, attrs: Record<string, string>) => {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    els.chart.append(el);
  };
  add("path", { d: g.burstPath, class: "line-burst" });
  add("path", { d: g.wpmPath, class: "line-wpm" });
  for (const d of g.errorDots) add("circle", { cx: String(d.x), cy: String(d.y), r: String(2 + d.n), class: "err-dot" });
}

function renderHistory(): void {
  els.history.textContent = "";
  for (const r of [...history.runs].reverse().slice(0, 10)) {
    const tr = document.createElement("tr");
    for (const v of [new Date(r.at).toLocaleString(), r.mode, fmtInt(r.netWpm), fmtPct(r.accuracy)]) {
      const td = document.createElement("td");
      td.textContent = v;
      tr.append(td);
    }
    els.history.append(tr);
  }
  const avg = history.recentAverage();
  $("#avg-wpm").textContent = avg === null ? "–" : fmtInt(avg);
}

/* ---------- controls ---------- */

function bindControls(): void {
  document.querySelectorAll<HTMLButtonElement>("[data-mode]").forEach((b) =>
    b.addEventListener("click", () => {
      const [kind, amount] = b.dataset.mode!.split("-") as [Kind, string];
      settings.kind = kind;
      settings.amount = Number(amount);
      document.querySelectorAll("[data-mode]").forEach((x) => x.classList.toggle("active", x === b));
      newTest();
    }),
  );
  const toggle = (id: string, key: "punctuation" | "numbers") =>
    $<HTMLInputElement>(id).addEventListener("change", (e) => {
      settings[key] = (e.target as HTMLInputElement).checked;
      newTest();
    });
  toggle("#opt-punct", "punctuation");
  toggle("#opt-num", "numbers");
  $<HTMLSelectElement>("#heat-mode").addEventListener("change", (e) => {
    settings.heatMode = (e.target as HTMLSelectElement).value as HeatmapMode;
    renderHeatmap();
  });
  $<HTMLSelectElement>("#heat-scope").addEventListener("change", (e) => {
    settings.heatScope = (e.target as HTMLSelectElement).value as "run" | "lifetime";
    renderHeatmap();
  });
  $("#btn-restart").addEventListener("click", () => newTest());
  $("#btn-practice").addEventListener("click", () => {
    focusKeys = weakestKeys(settings.heatScope === "run" ? lastRunStats : history.lifetimeKeyStats);
    newTest();
  });
  $("#btn-normal").addEventListener("click", () => {
    focusKeys = [];
    newTest();
  });
  $("#btn-clear").addEventListener("click", () => {
    history.clear();
    renderHistory();
    renderHeatmap();
  });
  els.passage.addEventListener("keydown", onKeyDown);
}

bindControls();
newTest();
renderHistory();
