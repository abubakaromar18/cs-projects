/**
 * Circuit model + simulation engine.
 *
 * A circuit is a directed graph: nodes are gates, edges are wires from a
 * node's single output to one input pin of another node. Each input pin has
 * at most one driver (a "net" with two drivers would be a short circuit), but
 * an output may fan out to any number of pins. Undriven inputs read as LOW.
 *
 * Simulation strategy
 * -------------------
 * 1. Combinational (acyclic) circuits are evaluated in a single pass in
 *    topological order (Kahn's algorithm), so each gate is computed exactly
 *    once, after all of its inputs: O(V + E).
 * 2. Sequential circuits contain feedback loops (e.g. an SR latch built from
 *    cross-coupled NOR gates). No topological order exists, so we fall back to
 *    fixed-point iteration: sweep all gates, updating values in place
 *    (Gauss–Seidel style), until a sweep changes nothing. Previous values are
 *    kept between runs, which is exactly what gives a latch its memory.
 *    If no fixed point is reached (a ring oscillator: a NOT gate feeding
 *    itself) the result is reported as unstable instead of looping forever.
 */
import { GATES, type GateKind } from "./gates.js";

export interface GateNode {
  readonly id: string;
  readonly kind: GateKind;
  x: number;
  y: number;
  label?: string;
  /** Switch position; only meaningful for INPUT nodes. */
  state?: boolean;
}

export interface Wire {
  readonly id: string;
  /** Node whose output drives this wire. */
  readonly from: string;
  /** Node whose input pin is driven. */
  readonly to: string;
  /** Index of the input pin on `to`. */
  readonly pin: number;
}

export interface SimulationResult {
  /** True when the circuit settled into a fixed point. */
  readonly stable: boolean;
  /** Number of sweeps used (1 for an acyclic circuit). */
  readonly sweeps: number;
  /** True when the circuit contains at least one feedback loop. */
  readonly sequential: boolean;
}

export class CircuitError extends Error {}

export class Circuit {
  private readonly nodes = new Map<string, GateNode>();
  private readonly wires = new Map<string, Wire>();
  /** Last computed output value of every node (for OUTPUT nodes: lamp state). */
  private readonly values = new Map<string, boolean>();
  private nextId = 1;

  // ---------------------------------------------------------------- editing

  addGate(kind: GateKind, x = 0, y = 0, opts: { id?: string; label?: string; state?: boolean } = {}): GateNode {
    const id = opts.id ?? this.freshId(kind.toLowerCase());
    if (this.nodes.has(id)) throw new CircuitError(`Duplicate node id "${id}"`);
    const node: GateNode = { id, kind, x, y };
    if (opts.label !== undefined) node.label = opts.label;
    if (kind === "INPUT") node.state = opts.state ?? false;
    this.nodes.set(id, node);
    this.values.set(id, false);
    return node;
  }

  /** Remove a gate and every wire touching it. */
  removeGate(id: string): void {
    if (!this.nodes.delete(id)) return;
    this.values.delete(id);
    for (const w of [...this.wires.values()]) {
      if (w.from === id || w.to === id) this.wires.delete(w.id);
    }
  }

  /**
   * Wire `from`'s output to input pin `pin` of `to`.
   * If that pin is already driven, the old wire is replaced (like re-plugging
   * a jumper on a breadboard).
   */
  connect(from: string, to: string, pin = 0): Wire {
    const src = this.requireNode(from);
    const dst = this.requireNode(to);
    if (GATES[src.kind].outputs === 0) throw new CircuitError(`${src.kind} "${from}" has no output`);
    const arity = GATES[dst.kind].inputs;
    if (!Number.isInteger(pin) || pin < 0 || pin >= arity) {
      throw new CircuitError(`${dst.kind} "${to}" has no input pin ${pin}`);
    }
    const existing = this.driverOf(to, pin);
    if (existing) this.wires.delete(existing.id);
    const wire: Wire = { id: this.freshId("w"), from, to, pin };
    this.wires.set(wire.id, wire);
    return wire;
  }

  disconnect(wireId: string): void {
    this.wires.delete(wireId);
  }

  setInput(id: string, state: boolean): void {
    const node = this.requireNode(id);
    if (node.kind !== "INPUT") throw new CircuitError(`"${id}" is not an INPUT`);
    node.state = state;
  }

  toggleInput(id: string): boolean {
    const node = this.requireNode(id);
    this.setInput(id, !node.state);
    return node.state!;
  }

  // ---------------------------------------------------------------- queries

  getNode(id: string): GateNode | undefined {
    return this.nodes.get(id);
  }

  allNodes(): GateNode[] {
    return [...this.nodes.values()];
  }

  allWires(): Wire[] {
    return [...this.wires.values()];
  }

  /** INPUT nodes sorted by label/id, which defines truth-table column order. */
  inputs(): GateNode[] {
    return this.byKind("INPUT");
  }

  outputs(): GateNode[] {
    return this.byKind("OUTPUT");
  }

  driverOf(nodeId: string, pin: number): Wire | undefined {
    for (const w of this.wires.values()) if (w.to === nodeId && w.pin === pin) return w;
    return undefined;
  }

  /** Current logic level of a node (its output, or for a lamp, whether it is lit). */
  value(id: string): boolean {
    return this.values.get(id) ?? false;
  }

  /** Logic level carried by a wire = the value of its driver. */
  wireValue(wire: Wire): boolean {
    return this.value(wire.from);
  }

  /** Read OUTPUT lamps as a {label: value} record. */
  readOutputs(): Record<string, boolean> {
    const out: Record<string, boolean> = {};
    for (const n of this.outputs()) out[n.label ?? n.id] = this.value(n.id);
    return out;
  }

  // ------------------------------------------------------------- simulation

  /**
   * Topological order of all nodes, or null when the graph has a cycle.
   * Kahn's algorithm: repeatedly emit nodes whose inputs are all resolved.
   */
  topologicalOrder(): GateNode[] | null {
    const indegree = new Map<string, number>();
    const fanout = new Map<string, string[]>();
    for (const id of this.nodes.keys()) {
      indegree.set(id, 0);
      fanout.set(id, []);
    }
    for (const w of this.wires.values()) {
      indegree.set(w.to, indegree.get(w.to)! + 1);
      fanout.get(w.from)!.push(w.to);
    }
    // Seed queue in insertion order so the result is deterministic.
    const queue = [...this.nodes.keys()].filter((id) => indegree.get(id) === 0);
    const order: GateNode[] = [];
    for (let head = 0; head < queue.length; head++) {
      const id = queue[head]!;
      order.push(this.nodes.get(id)!);
      for (const next of fanout.get(id)!) {
        const d = indegree.get(next)! - 1;
        indegree.set(next, d);
        if (d === 0) queue.push(next);
      }
    }
    return order.length === this.nodes.size ? order : null;
  }

  /** Propagate input values through the circuit. */
  simulate(maxSweeps = 64 + 4 * this.nodes.size): SimulationResult {
    const driverIndex = this.buildDriverIndex();
    const order = this.topologicalOrder();

    if (order) {
      for (const node of order) this.values.set(node.id, this.evaluateNode(node, driverIndex));
      return { stable: true, sweeps: 1, sequential: false };
    }

    // Feedback present: iterate to a fixed point. Sources first so that the
    // freshest switch positions are visible during the first sweep.
    const nodes = this.allNodes().sort((a, b) => Number(b.kind === "INPUT") - Number(a.kind === "INPUT"));
    for (let sweep = 1; sweep <= maxSweeps; sweep++) {
      let changed = false;
      for (const node of nodes) {
        const next = this.evaluateNode(node, driverIndex);
        if (next !== this.values.get(node.id)) {
          this.values.set(node.id, next);
          changed = true;
        }
      }
      if (!changed) return { stable: true, sweeps: sweep, sequential: true };
    }
    return { stable: false, sweeps: maxSweeps, sequential: true };
  }

  /** Copy of every node's current value (e.g. to explore inputs without losing latch memory). */
  snapshotState(): Map<string, boolean> {
    return new Map(this.values);
  }

  restoreState(snapshot: ReadonlyMap<string, boolean>): void {
    for (const id of this.values.keys()) this.values.set(id, snapshot.get(id) ?? false);
  }

  /** Reset all remembered values to LOW (clears latch memory). */
  resetState(): void {
    for (const id of this.values.keys()) this.values.set(id, false);
  }

  // ---------------------------------------------------------------- helpers

  private evaluateNode(node: GateNode, driverIndex: Map<string, string>): boolean {
    if (node.kind === "INPUT") return node.state ?? false;
    const spec = GATES[node.kind];
    const ins: boolean[] = [];
    for (let pin = 0; pin < spec.inputs; pin++) {
      const driver = driverIndex.get(`${node.id}:${pin}`);
      ins.push(driver !== undefined ? this.value(driver) : false);
    }
    return spec.evaluate(ins);
  }

  /** "nodeId:pin" -> driving node id, so each evaluation is O(arity). */
  private buildDriverIndex(): Map<string, string> {
    const index = new Map<string, string>();
    for (const w of this.wires.values()) index.set(`${w.to}:${w.pin}`, w.from);
    return index;
  }

  private byKind(kind: GateKind): GateNode[] {
    return this.allNodes()
      .filter((n) => n.kind === kind)
      .sort((a, b) => (a.label ?? a.id).localeCompare(b.label ?? b.id, undefined, { numeric: true }));
  }

  private requireNode(id: string): GateNode {
    const node = this.nodes.get(id);
    if (!node) throw new CircuitError(`Unknown node "${id}"`);
    return node;
  }

  private freshId(prefix: string): string {
    let id: string;
    do id = `${prefix}${this.nextId++}`;
    while (this.nodes.has(id) || this.wires.has(id));
    return id;
  }
}
