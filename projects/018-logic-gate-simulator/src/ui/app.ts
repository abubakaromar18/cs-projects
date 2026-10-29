/**
 * Browser front-end: an SVG schematic editor wired to the simulation core.
 *
 * Interaction summary
 *   - Drag a palette button onto the board (or click it) to add a gate.
 *   - Drag a gate's body to move it.
 *   - Drag from an output pin (right) to an input pin (left) to make a wire.
 *   - Click an INPUT switch to toggle it. Double-click an INPUT/OUTPUT to rename.
 *   - Click a wire to delete it. Right-click a gate, or select it and press
 *     Delete/Backspace, to remove it.
 *
 * The whole board is re-rendered from the model after each change; circuits
 * of a few hundred gates redraw well within a frame, and it keeps the view a
 * pure function of the model (no stale DOM state to reconcile).
 */
import { Circuit, type GateNode, type SimulationResult } from "../core/circuit.js";
import { GATES, PALETTE, type GateKind } from "../core/gates.js";
import { EXAMPLES } from "../core/library.js";
import { sumOfProducts, truthTable } from "../core/analysis.js";
import { fromJSON, toJSON } from "../core/serialize.js";
import { gateSize, inputPinPos, outputPinPos, PIN_RADIUS, snap, wirePath, type Point } from "./geometry.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const STORAGE_KEY = "logic-gate-simulator:v1";
/** Above this many inputs the live truth table is skipped (2^n rows). */
const LIVE_TABLE_LIMIT = 9;
const DEFAULT_EXAMPLE = "Full adder";

// ------------------------------------------------------------------ DOM refs

function $<T extends Element>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) throw new Error(`Missing element ${selector}`);
  return found;
}

const board = $<SVGSVGElement>("#board");
const wireLayer = $<SVGGElement>("#wires");
const gateLayer = $<SVGGElement>("#gates");
const preview = $<SVGPathElement>("#preview");
const palette = $<HTMLDivElement>("#palette");
const exampleSelect = $<HTMLSelectElement>("#example");
const statusEl = $<HTMLParagraphElement>("#status");
const tableEl = $<HTMLDivElement>("#truth-table");
const importInput = $<HTMLInputElement>("#import-file");

// --------------------------------------------------------------------- state

let circuit: Circuit = loadSaved() ?? EXAMPLES[DEFAULT_EXAMPLE]!();
let selected: string | null = null;
let result: SimulationResult = circuit.simulate();

type Gesture =
  | { mode: "idle" }
  | { mode: "drag"; id: string; offset: Point; start: Point; moved: boolean }
  | { mode: "wire"; from: string; start: Point };
let gesture: Gesture = { mode: "idle" };

// ------------------------------------------------------------------- helpers

function svgEl<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | number> = {},
  parent?: Element,
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  parent?.appendChild(node);
  return node;
}

/** Convert a mouse/pointer event to board (SVG user-space) coordinates. */
function boardPoint(evt: { clientX: number; clientY: number }): Point {
  const ctm = board.getScreenCTM();
  if (!ctm) return { x: evt.clientX, y: evt.clientY };
  const p = new DOMPoint(evt.clientX, evt.clientY).matrixTransform(ctm.inverse());
  return { x: p.x, y: p.y };
}

/** Pick the next unused label: A, B, C… for inputs, Y0, Y1… for outputs. */
function nextLabel(kind: GateKind): string | undefined {
  const used = new Set(circuit.allNodes().map((n) => n.label ?? n.id));
  if (kind === "INPUT") {
    for (let i = 0; ; i++) {
      const label = i < 26 ? String.fromCharCode(65 + i) : `X${i}`;
      if (!used.has(label)) return label;
    }
  }
  if (kind === "OUTPUT") {
    for (let i = 0; ; i++) if (!used.has(`Y${i}`)) return `Y${i}`;
  }
  return undefined;
}

function addGateAt(kind: GateKind, center: Point): void {
  const { w, h } = gateSize(kind);
  const label = nextLabel(kind);
  const node = circuit.addGate(kind, snap(center.x - w / 2), snap(center.y - h / 2), label ? { label } : {});
  selected = node.id;
  update();
}

// ----------------------------------------------------------------- rendering

function render(): void {
  wireLayer.replaceChildren();
  gateLayer.replaceChildren();

  for (const wire of circuit.allWires()) {
    const src = circuit.getNode(wire.from)!;
    const dst = circuit.getNode(wire.to)!;
    const a = outputPinPos(src.kind, src.x, src.y);
    const b = inputPinPos(dst.kind, dst.x, dst.y, wire.pin);
    const d = wirePath(a, b);
    const on = circuit.wireValue(wire);
    // A wide transparent "hit" path makes thin wires easy to click.
    svgEl("path", { d, class: "wire-hit", "data-wire": wire.id }, wireLayer);
    svgEl("path", { d, class: `wire ${on ? "on" : "off"}` }, wireLayer);
  }

  for (const node of circuit.allNodes()) drawGate(node);
}

function drawGate(node: GateNode): void {
  const spec = GATES[node.kind];
  const { w, h } = gateSize(node.kind);
  const on = circuit.value(node.id);
  const g = svgEl("g", {
    class: `gate kind-${node.kind.toLowerCase()} ${on ? "on" : "off"} ${node.id === selected ? "selected" : ""}`,
    transform: `translate(${node.x} ${node.y})`,
    "data-node": node.id,
  }, gateLayer);

  if (node.kind === "OUTPUT") {
    svgEl("rect", { class: "body", width: w, height: h, rx: 20 }, g);
    svgEl("circle", { class: "lamp", cx: w / 2 + 4, cy: h / 2, r: 11 }, g);
  } else if (node.kind === "INPUT") {
    svgEl("rect", { class: "body", width: w, height: h, rx: 6 }, g);
    svgEl("rect", { class: "switch", x: 10, y: 10, width: 28, height: 20, rx: 10 }, g);
    svgEl("circle", { class: "knob", cx: on ? 28 : 20, cy: 20, r: 7 }, g);
  } else {
    svgEl("rect", { class: "body", width: w, height: h, rx: 8 }, g);
    const sym = svgEl("text", { class: "symbol", x: w / 2, y: h / 2 + 1 }, g);
    sym.textContent = spec.symbol;
    const kind = svgEl("text", { class: "kind", x: w / 2, y: h + 13 }, g);
    kind.textContent = node.kind;
  }

  if (node.label) {
    const t = svgEl("text", { class: "label", x: node.kind === "OUTPUT" ? w + 10 : -10, y: h / 2 + 1 }, g);
    t.setAttribute("text-anchor", node.kind === "OUTPUT" ? "start" : "end");
    t.textContent = node.label;
  }

  // Pins are drawn in gate-local coordinates.
  for (let pin = 0; pin < spec.inputs; pin++) {
    const p = inputPinPos(node.kind, 0, 0, pin);
    svgEl("circle", { class: "pin pin-in", cx: p.x, cy: p.y, r: PIN_RADIUS, "data-node": node.id, "data-pin": pin }, g);
  }
  if (spec.outputs > 0) {
    const p = outputPinPos(node.kind, 0, 0);
    svgEl("circle", { class: `pin pin-out ${on ? "on" : ""}`, cx: p.x, cy: p.y, r: PIN_RADIUS, "data-node": node.id }, g);
  }
}

function renderStatus(): void {
  const gates = circuit.allNodes().filter((n) => n.kind !== "INPUT" && n.kind !== "OUTPUT").length;
  const kind = result.sequential ? "sequential (has feedback)" : "combinational";
  const stability = result.stable
    ? `settled in ${result.sweeps} sweep${result.sweeps === 1 ? "" : "s"}`
    : "⚠ unstable — oscillates, no fixed point";
  statusEl.textContent = `${gates} gates · ${circuit.allWires().length} wires · ${kind} · ${stability}`;
  statusEl.classList.toggle("warn", !result.stable);
}

function renderTruthTable(): void {
  tableEl.replaceChildren();
  const ins = circuit.inputs();
  const outs = circuit.outputs();
  const note = (text: string) => {
    const p = document.createElement("p");
    p.className = "note";
    p.textContent = text;
    tableEl.appendChild(p);
  };
  if (ins.length === 0 || outs.length === 0) return note("Add at least one INPUT and one OUTPUT.");
  if (ins.length > LIVE_TABLE_LIMIT) return note(`${ins.length} inputs → ${2 ** ins.length} rows; too many to list live.`);
  if (result.sequential) note("Sequential circuit: outputs depend on history. Rows below start from the current state.");

  const t = truthTable(circuit);
  const current = ins.map((n) => n.state ?? false);
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  for (const name of t.inputs) head.appendChild(Object.assign(document.createElement("th"), { textContent: name }));
  for (const name of t.outputs) head.appendChild(Object.assign(document.createElement("th"), { textContent: name, className: "out" }));
  const body = table.createTBody();
  for (const row of t.rows) {
    const tr = body.insertRow();
    if (row.slice(0, ins.length).every((b, i) => b === current[i])) tr.className = "current";
    row.forEach((bit, i) => {
      const td = tr.insertCell();
      td.textContent = bit ? "1" : "0";
      if (i >= ins.length) td.className = bit ? "out hi" : "out";
    });
  }
  tableEl.appendChild(table);

  if (ins.length <= 4 && !result.sequential) {
    const dl = document.createElement("dl");
    t.outputs.forEach((name, i) => {
      dl.appendChild(Object.assign(document.createElement("dt"), { textContent: `${name} =` }));
      dl.appendChild(Object.assign(document.createElement("dd"), { textContent: sumOfProducts(t, i) }));
    });
    tableEl.appendChild(dl);
  }
}

/** Re-simulate, redraw everything and persist. */
function update(): void {
  result = circuit.simulate();
  render();
  renderStatus();
  renderTruthTable();
  save();
}

// --------------------------------------------------------------- persistence

function save(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toJSON(circuit)));
  } catch {
    /* storage unavailable (private mode): the app still works, just unsaved */
  }
}

function loadSaved(): Circuit | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? fromJSON(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function replaceCircuit(next: Circuit): void {
  circuit = next;
  selected = null;
  update();
}

// --------------------------------------------------------------- interaction

board.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  const target = e.target as Element;
  const p = boardPoint(e);

  const wireId = target.getAttribute("data-wire");
  if (wireId) {
    circuit.disconnect(wireId);
    update();
    return;
  }
  if (target.classList.contains("pin-out")) {
    const from = target.getAttribute("data-node")!;
    const node = circuit.getNode(from)!;
    gesture = { mode: "wire", from, start: outputPinPos(node.kind, node.x, node.y) };
    preview.setAttribute("d", wirePath(gesture.start, p));
    preview.style.display = "";
    board.setPointerCapture(e.pointerId);
    return;
  }
  const group = target.closest("[data-node]");
  if (group) {
    const id = group.getAttribute("data-node")!;
    const node = circuit.getNode(id)!;
    selected = id;
    gesture = { mode: "drag", id, offset: { x: p.x - node.x, y: p.y - node.y }, start: p, moved: false };
    board.setPointerCapture(e.pointerId);
    render();
    return;
  }
  selected = null;
  render();
});

board.addEventListener("pointermove", (e) => {
  const p = boardPoint(e);
  if (gesture.mode === "drag") {
    if (!gesture.moved && Math.hypot(p.x - gesture.start.x, p.y - gesture.start.y) < 4) return;
    gesture.moved = true;
    const node = circuit.getNode(gesture.id)!;
    node.x = snap(p.x - gesture.offset.x);
    node.y = snap(p.y - gesture.offset.y);
    render(); // position only: no need to re-simulate
  } else if (gesture.mode === "wire") {
    preview.setAttribute("d", wirePath(gesture.start, p));
  }
});

board.addEventListener("pointerup", (e) => {
  if (gesture.mode === "wire") {
    preview.style.display = "none";
    finishWire(gesture.from, e);
  } else if (gesture.mode === "drag") {
    const node = circuit.getNode(gesture.id);
    if (!gesture.moved && node?.kind === "INPUT") circuit.toggleInput(node.id);
    update();
  }
  gesture = { mode: "idle" };
});

board.addEventListener("pointercancel", () => {
  preview.style.display = "none";
  gesture = { mode: "idle" };
});

/** Drop a wire on an input pin, or on a gate body (first free pin wins). */
function finishWire(from: string, e: PointerEvent): void {
  const under = document.elementFromPoint(e.clientX, e.clientY);
  if (!under) return;
  let to: string | null = null;
  let pin = 0;
  if (under.classList.contains("pin-in")) {
    to = under.getAttribute("data-node");
    pin = Number(under.getAttribute("data-pin"));
  } else {
    const group = under.closest("[data-node]");
    to = group?.getAttribute("data-node") ?? null;
    if (to) {
      const arity = GATES[circuit.getNode(to)!.kind].inputs;
      const free = [...Array(arity).keys()].find((i) => !circuit.driverOf(to!, i));
      if (arity === 0) to = null;
      else pin = free ?? 0;
    }
  }
  if (!to) return;
  try {
    circuit.connect(from, to, pin);
  } catch (err) {
    flash((err as Error).message);
  }
  update();
}

board.addEventListener("dblclick", (e) => {
  const id = (e.target as Element).closest("[data-node]")?.getAttribute("data-node");
  const node = id ? circuit.getNode(id) : undefined;
  if (!node || (node.kind !== "INPUT" && node.kind !== "OUTPUT")) return;
  // The two clicks of a double-click toggle an INPUT twice, so it ends where it started.
  const name = window.prompt("Label", node.label ?? "");
  if (name !== null && name.trim()) node.label = name.trim().slice(0, 12);
  update();
});

board.addEventListener("contextmenu", (e) => {
  const id = (e.target as Element).closest("[data-node]")?.getAttribute("data-node");
  if (!id) return;
  e.preventDefault();
  circuit.removeGate(id);
  if (selected === id) selected = null;
  update();
});

window.addEventListener("keydown", (e) => {
  if (!selected || (e.target as HTMLElement).closest("input, select, textarea")) return;
  if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    circuit.removeGate(selected);
    selected = null;
    update();
  }
});

// Palette: HTML5 drag-and-drop onto the board, or plain click.
for (const kind of PALETTE) {
  const button = document.createElement("button");
  button.type = "button";
  button.draggable = true;
  button.className = "palette-item";
  button.innerHTML = `<span class="sym"></span><span></span>`;
  button.firstElementChild!.textContent = GATES[kind].symbol;
  button.lastElementChild!.textContent = kind;
  button.title = `Drag onto the board (or click) to add ${kind}`;
  button.addEventListener("dragstart", (e) => e.dataTransfer?.setData("application/x-gate", kind));
  button.addEventListener("click", () => {
    const box = board.viewBox.baseVal;
    const n = circuit.allNodes().length;
    addGateAt(kind, { x: box.x + box.width / 2 + (n % 5) * 20, y: box.y + box.height / 2 + (n % 5) * 20 });
  });
  palette.appendChild(button);
}
board.addEventListener("dragover", (e) => e.preventDefault());
board.addEventListener("drop", (e) => {
  e.preventDefault();
  const kind = e.dataTransfer?.getData("application/x-gate");
  if (kind && (PALETTE as readonly string[]).includes(kind)) addGateAt(kind as GateKind, boardPoint(e));
});

// Toolbar
for (const name of Object.keys(EXAMPLES)) exampleSelect.add(new Option(name, name));
exampleSelect.value = "";
exampleSelect.addEventListener("change", () => {
  const build = EXAMPLES[exampleSelect.value];
  if (build) replaceCircuit(build());
  exampleSelect.value = "";
});
$("#clear").addEventListener("click", () => replaceCircuit(new Circuit()));
$("#reset").addEventListener("click", () => {
  circuit.resetState();
  update();
});
$("#export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(toJSON(circuit), null, 2)], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "circuit.json" });
  a.click();
  URL.revokeObjectURL(a.href);
});
$("#import").addEventListener("click", () => importInput.click());
importInput.addEventListener("change", async () => {
  const file = importInput.files?.[0];
  importInput.value = "";
  if (!file) return;
  try {
    replaceCircuit(fromJSON(JSON.parse(await file.text())));
  } catch (err) {
    flash((err as Error).message);
  }
});

function flash(message: string): void {
  statusEl.textContent = message;
  statusEl.classList.add("warn");
  window.setTimeout(renderStatus, 2500);
}

update();
