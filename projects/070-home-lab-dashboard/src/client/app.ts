/**
 * Browser entry point: fetches /api/status, renders the cards, and polls.
 *
 * All text is inserted with textContent / setAttribute (never innerHTML),
 * so a service name like "<img onerror=…>" is shown literally.
 */
import type { ServiceStatus, StatusSnapshot } from "../shared/types.js";
import {
  HEALTH_LABEL, formatLatency, formatUptime, groupServices, matchesFilter,
  overallHealth, relativeTime, safeHref, sparkline,
} from "./format.js";

const SPARK_SLOTS = 30;
const SPARK_HEIGHT = 24;
const SVG_NS = "http://www.w3.org/2000/svg";

const $ = <T extends HTMLElement>(sel: string): T => {
  const el = document.querySelector<T>(sel);
  if (!el) throw new Error(`missing element ${sel}`);
  return el;
};

const els = {
  title: $<HTMLHeadingElement>("#title"),
  banner: $<HTMLDivElement>("#banner"),
  groups: $<HTMLElement>("#groups"),
  filter: $<HTMLInputElement>("#filter"),
  refresh: $<HTMLButtonElement>("#refresh"),
  updated: $<HTMLSpanElement>("#updated"),
  error: $<HTMLDivElement>("#error"),
};

let snapshot: StatusSnapshot | undefined;
let pollTimer: number | undefined;

/** Small helper to build an element with a class and optional text. */
function h<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function renderSparkline(s: ServiceStatus): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "spark");
  svg.setAttribute("viewBox", `0 0 ${SPARK_SLOTS * 4} ${SPARK_HEIGHT}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `Recent checks for ${s.name}`);
  for (const bar of sparkline(s.history, SPARK_SLOTS, SPARK_HEIGHT)) {
    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", String(bar.x * 4));
    rect.setAttribute("y", String(SPARK_HEIGHT - bar.height));
    rect.setAttribute("width", "3");
    rect.setAttribute("height", String(bar.height));
    rect.setAttribute("class", `bar ${bar.health}`);
    svg.appendChild(rect);
  }
  return svg;
}

function renderCard(s: ServiceStatus, now: number): HTMLElement {
  const href = safeHref(s.url);
  const card = h(href ? "a" : "div", `card ${s.current.health}`);
  if (href && card instanceof HTMLAnchorElement) {
    card.href = href;
    card.target = "_blank";
    card.rel = "noopener noreferrer";
  }

  const head = h("div", "card-head");
  head.append(h("span", "icon", s.icon ?? "🔗"));
  const names = h("div", "names");
  names.append(h("span", "name", s.name), h("span", "host", new URL(s.url).host || s.url));
  head.append(names);
  const pill = h("span", `pill ${s.current.health}`, HEALTH_LABEL[s.current.health]);
  pill.title = s.current.detail;
  head.append(pill);
  card.append(head);

  if (s.description) card.append(h("p", "desc", s.description));

  if (s.checkType !== "none") {
    const stats = h("div", "stats");
    stats.append(
      stat("Latency", formatLatency(s.current.latencyMs)),
      stat("Uptime", formatUptime(s.uptimePercent)),
      stat("Checked", relativeTime(s.current.checkedAt, now)),
    );
    card.append(stats, renderSparkline(s), h("div", "detail", s.current.detail));
  }
  return card;
}

function stat(label: string, value: string): HTMLElement {
  const el = h("div", "stat");
  el.append(h("span", "label", label), h("span", "value", value));
  return el;
}

function render(): void {
  if (!snapshot) return;
  const now = Date.now();
  document.title = snapshot.title;
  els.title.textContent = snapshot.title;

  const overall = overallHealth(snapshot.summary);
  const { up, degraded, down, unknown } = snapshot.summary;
  els.banner.className = `banner ${overall}`;
  els.banner.textContent =
    overall === "down" ? `${down} service${down === 1 ? "" : "s"} down`
    : overall === "degraded" ? `All reachable, ${degraded} slow`
    : overall === "up" ? "All systems operational"
    : "Waiting for first check…";
  els.banner.title = `${up} up · ${degraded} slow · ${down} down · ${unknown} unchecked`;
  els.updated.textContent = `Updated ${relativeTime(snapshot.generatedAt, now)}`;

  const query = els.filter.value;
  const frag = document.createDocumentFragment();
  for (const [group, services] of groupServices(snapshot.services)) {
    const visible = services.filter((s) => matchesFilter(s, query));
    if (visible.length === 0) continue;
    const section = h("section", "group");
    section.append(h("h2", undefined, group));
    const grid = h("div", "grid");
    for (const s of visible) grid.append(renderCard(s, now));
    section.append(grid);
    frag.append(section);
  }
  if (!frag.hasChildNodes()) frag.append(h("p", "empty", "No services match your filter."));
  els.groups.replaceChildren(frag);
}

async function load(method: "GET" | "POST" = "GET"): Promise<void> {
  const endpoint = method === "POST" ? "/api/refresh" : "/api/status";
  try {
    const res = await fetch(endpoint, { method, cache: "no-store" });
    if (!res.ok) throw new Error(`${endpoint} returned HTTP ${res.status}`);
    snapshot = (await res.json()) as StatusSnapshot;
    els.error.hidden = true;
    render();
  } catch (err) {
    els.error.textContent = `Can't reach the dashboard server: ${(err as Error).message}`;
    els.error.hidden = false;
  }
}

function schedulePolling(): void {
  window.clearInterval(pollTimer);
  const seconds = Math.max(5, snapshot?.intervalSeconds ?? 30);
  pollTimer = window.setInterval(() => {
    if (document.visibilityState === "visible") void load();
  }, seconds * 1000);
}

els.filter.addEventListener("input", render);
els.refresh.addEventListener("click", async () => {
  els.refresh.disabled = true;
  els.refresh.classList.add("spinning");
  await load("POST");
  els.refresh.disabled = false;
  els.refresh.classList.remove("spinning");
});
// "/" focuses the search box, Escape clears it.
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== els.filter) {
    e.preventDefault();
    els.filter.focus();
  } else if (e.key === "Escape" && document.activeElement === els.filter) {
    els.filter.value = "";
    render();
  }
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") void load();
});
// Keep the "Checked 12s ago" labels moving between polls.
window.setInterval(render, 5000);

void load().then(schedulePolling);
