/**
 * JSON (de)serialization so circuits can be saved, shared and reloaded.
 * Parsing validates everything: untrusted JSON never reaches the engine raw.
 */
import { Circuit } from "./circuit.js";
import { isGateKind, type GateKind } from "./gates.js";

export const FORMAT_VERSION = 1;

export interface CircuitJSON {
  version: number;
  nodes: { id: string; kind: GateKind; x: number; y: number; label?: string; state?: boolean }[];
  wires: { from: string; to: string; pin: number }[];
}

export function toJSON(circuit: Circuit): CircuitJSON {
  return {
    version: FORMAT_VERSION,
    nodes: circuit.allNodes().map(({ id, kind, x, y, label, state }) => ({
      id,
      kind,
      x: Math.round(x),
      y: Math.round(y),
      ...(label !== undefined ? { label } : {}),
      ...(kind === "INPUT" ? { state: state ?? false } : {}),
    })),
    wires: circuit.allWires().map(({ from, to, pin }) => ({ from, to, pin })),
  };
}

export function fromJSON(data: unknown): Circuit {
  const fail = (msg: string): never => {
    throw new SyntaxError(`Invalid circuit file: ${msg}`);
  };
  if (typeof data !== "object" || data === null) fail("not an object");
  const obj = data as Record<string, unknown>;
  if (obj.version !== FORMAT_VERSION) fail(`unsupported version ${String(obj.version)}`);
  if (!Array.isArray(obj.nodes) || !Array.isArray(obj.wires)) fail("missing nodes/wires");

  const circuit = new Circuit();
  for (const raw of obj.nodes as unknown[]) {
    const n = raw as Record<string, unknown>;
    if (typeof n.id !== "string" || !n.id) fail("node without id");
    if (!isGateKind(n.kind)) fail(`unknown gate kind ${String(n.kind)}`);
    const x = Number(n.x);
    const y = Number(n.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) fail(`bad position for ${String(n.id)}`);
    circuit.addGate(n.kind as GateKind, x, y, {
      id: n.id as string,
      ...(typeof n.label === "string" ? { label: n.label } : {}),
      ...(typeof n.state === "boolean" ? { state: n.state } : {}),
    });
  }
  for (const raw of obj.wires as unknown[]) {
    const w = raw as Record<string, unknown>;
    if (typeof w.from !== "string" || typeof w.to !== "string") fail("wire endpoints must be strings");
    circuit.connect(w.from as string, w.to as string, Number(w.pin ?? 0));
  }
  circuit.simulate();
  return circuit;
}
