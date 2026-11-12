/**
 * Text rendering: the "visual breakdown" that shows exactly which bits of an
 * address belong to the network and which to the host.
 */
import { formatIp, toBinary } from "./ipv4.js";
import { Subnet, type SubnetReport, type VlsmAllocation } from "./subnet.js";

export interface Style {
  net: (s: string) => string;
  host: (s: string) => string;
  dim: (s: string) => string;
  bold: (s: string) => string;
}

const ansi = (code: number) => (s: string) => `\x1b[${code}m${s}\x1b[0m`;

export const COLOR: Style = { net: ansi(36), host: ansi(33), dim: ansi(2), bold: ansi(1) };
export const PLAIN: Style = { net: (s) => s, host: (s) => s, dim: (s) => s, bold: (s) => s };

/**
 * Binary form of `value` grouped into octets, with the first `prefix` bits
 * styled as network bits and the remainder as host bits.
 */
export function bitString(value: number, prefix: number, style: Style = PLAIN): string {
  const bits = toBinary(value);
  const octets: string[] = [];
  for (let o = 0; o < 4; o++) {
    let chunk = "";
    for (let b = o * 8; b < o * 8 + 8; b++) {
      chunk += b < prefix ? style.net(bits[b]!) : style.host(bits[b]!);
    }
    octets.push(chunk);
  }
  return octets.join(".");
}

/**
 * Marker line drawn under a bitString: "n" for network bits, "h" for host
 * bits, with a "|" at the prefix boundary when it falls inside an octet.
 */
export function boundaryRuler(prefix: number): string {
  let line = "";
  for (let b = 0; b < 32; b++) {
    if (b > 0 && b % 8 === 0) line += ".";
    line += b < prefix ? "n" : "h";
  }
  return line;
}

function row(label: string, value: string, style: Style): string {
  return `  ${style.dim(label.padEnd(18))}${value}`;
}

export function renderReport(r: SubnetReport, style: Style = PLAIN): string {
  const subnet = Subnet.parse(r.cidr);
  const p = subnet.prefix;
  const addr = Subnet.parse(r.address).network;
  const lines = [
    style.bold(`Subnet ${r.cidr}`),
    "",
    row("Address", r.address, style),
    row("Netmask", `${r.netmask} = /${p}`, style),
    row("Wildcard", r.wildcard, style),
    row("Network", r.network, style),
    row("Broadcast", r.broadcast, style),
    row("Host range", `${r.firstHost} – ${r.lastHost}`, style),
    row("Total addresses", r.totalAddresses.toLocaleString("en-US"), style),
    row("Usable hosts", r.usableHosts.toLocaleString("en-US"), style),
    row("Class / scope", `${r.addressClass} · ${r.scope}`, style),
    "",
    style.bold("Bit breakdown") +
      style.dim(`  (${p} network bits, ${32 - p} host bits)`),
    "",
    row("", boundaryRuler(p), style),
    row("Address", bitString(addr, p, style), style),
    row("Netmask", bitString(subnet.mask, p, style), style),
    row("Network", bitString(subnet.network, p, style), style),
    row("Broadcast", bitString(subnet.broadcast, p, style), style),
  ];
  return lines.join("\n");
}

export function renderSplit(parent: Subnet, children: Subnet[], limit = 64): string {
  const lines = [`${parent} → ${children.length} × /${children[0]?.prefix}`, ""];
  const header = `  ${"#".padStart(5)}  ${"Subnet".padEnd(19)}${"Host range".padEnd(34)}Broadcast`;
  lines.push(header);
  children.slice(0, limit).forEach((s, i) => {
    const range = `${formatIp(s.firstHost)} – ${formatIp(s.lastHost)}`;
    lines.push(`  ${String(i + 1).padStart(5)}  ${s.toString().padEnd(19)}${range.padEnd(34)}${formatIp(s.broadcast)}`);
  });
  if (children.length > limit) lines.push(`  … ${children.length - limit} more`);
  return lines.join("\n");
}

export function renderVlsm(parent: Subnet, plan: VlsmAllocation[]): string {
  const used = plan.reduce((sum, a) => sum + a.subnet.size, 0);
  const lines = [`VLSM plan for ${parent}`, ""];
  lines.push(`  ${"Name".padEnd(14)}${"Need".padStart(7)}  ${"Subnet".padEnd(19)}${"Usable".padStart(8)}  Host range`);
  for (const a of plan) {
    const s = a.subnet;
    lines.push(
      `  ${a.name.padEnd(14)}${String(a.hosts).padStart(7)}  ${s.toString().padEnd(19)}` +
        `${String(s.usableHosts).padStart(8)}  ${formatIp(s.firstHost)} – ${formatIp(s.lastHost)}`,
    );
  }
  const pct = ((used / parent.size) * 100).toFixed(1);
  lines.push("", `  ${used} of ${parent.size} addresses allocated (${pct}%)`);
  return lines.join("\n");
}
