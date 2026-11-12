/**
 * CIDR blocks and the operations network engineers do on them:
 * describe, split, VLSM-allocate, and summarise.
 */
import {
  ParseError,
  addressClass,
  addressScope,
  assertPrefix,
  formatIp,
  maskToPrefix,
  parseIp,
  prefixToMask,
} from "./ipv4.js";

/** An immutable CIDR block, always stored in canonical (network) form. */
export class Subnet {
  readonly network: number;
  readonly prefix: number;

  constructor(address: number, prefix: number) {
    assertPrefix(prefix);
    this.prefix = prefix;
    this.network = (address & prefixToMask(prefix)) >>> 0;
  }

  /**
   * Parse "10.0.0.5/8", "10.0.0.5 255.0.0.0", "10.0.0.5/255.0.0.0" or a bare
   * address (treated as /32). Host bits are allowed and simply masked off.
   */
  static parse(text: string): Subnet {
    const trimmed = text.trim();
    const [addr, suffix, ...rest] = trimmed.split(/[\s/]+/);
    if (!addr || rest.length > 0) throw new ParseError(`cannot parse "${text}"`);
    const ip = parseIp(addr);
    if (suffix === undefined) return new Subnet(ip, 32);
    if (suffix.includes(".")) return new Subnet(ip, maskToPrefix(parseIp(suffix)));
    if (!/^\d{1,2}$/.test(suffix)) throw new ParseError(`invalid prefix "/${suffix}"`);
    return new Subnet(ip, Number(suffix));
  }

  get mask(): number {
    return prefixToMask(this.prefix);
  }

  get wildcard(): number {
    return ~this.mask >>> 0;
  }

  get broadcast(): number {
    return (this.network | this.wildcard) >>> 0;
  }

  /** Total addresses in the block (2^(32-prefix)); a float is exact up to 2^32. */
  get size(): number {
    return 2 ** (32 - this.prefix);
  }

  /**
   * Usable host addresses. Network and broadcast are reserved, except that
   * /31 point-to-point links (RFC 3021) and /32 host routes use every address.
   */
  get usableHosts(): number {
    if (this.prefix >= 31) return this.size;
    return this.size - 2;
  }

  get firstHost(): number {
    return this.prefix >= 31 ? this.network : this.network + 1;
  }

  get lastHost(): number {
    return this.prefix >= 31 ? this.broadcast : this.broadcast - 1;
  }

  contains(ip: number): boolean {
    return ((ip & this.mask) >>> 0) === this.network;
  }

  /** True if `other` lies entirely inside this block. */
  covers(other: Subnet): boolean {
    return other.prefix >= this.prefix && this.contains(other.network);
  }

  overlaps(other: Subnet): boolean {
    return this.covers(other) || other.covers(this);
  }

  /** Split into equal child subnets of length `newPrefix`. */
  split(newPrefix: number): Subnet[] {
    assertPrefix(newPrefix);
    if (newPrefix < this.prefix) {
      throw new ParseError(`/${newPrefix} is larger than /${this.prefix}`);
    }
    const count = 2 ** (newPrefix - this.prefix);
    if (count > 65536) {
      throw new ParseError(`refusing to list ${count} subnets (limit 65536)`);
    }
    const step = 2 ** (32 - newPrefix);
    const out: Subnet[] = [];
    for (let i = 0; i < count; i++) out.push(new Subnet(this.network + i * step, newPrefix));
    return out;
  }

  toString(): string {
    return `${formatIp(this.network)}/${this.prefix}`;
  }
}

/** Everything the "info" view shows, computed once. */
export interface SubnetReport {
  input: string;
  address: string;
  cidr: string;
  netmask: string;
  wildcard: string;
  network: string;
  broadcast: string;
  firstHost: string;
  lastHost: string;
  totalAddresses: number;
  usableHosts: number;
  addressClass: string;
  scope: string;
}

export function describe(text: string): SubnetReport {
  const subnet = Subnet.parse(text);
  const address = parseIp(text.trim().split(/[\s/]+/)[0]!);
  return {
    input: text.trim(),
    address: formatIp(address),
    cidr: subnet.toString(),
    netmask: formatIp(subnet.mask),
    wildcard: formatIp(subnet.wildcard),
    network: formatIp(subnet.network),
    broadcast: formatIp(subnet.broadcast),
    firstHost: formatIp(subnet.firstHost),
    lastHost: formatIp(subnet.lastHost),
    totalAddresses: subnet.size,
    usableHosts: subnet.usableHosts,
    addressClass: addressClass(address),
    scope: addressScope(address),
  };
}

/** Smallest prefix length whose block has at least `hosts` usable addresses. */
export function prefixForHosts(hosts: number): number {
  if (!Number.isInteger(hosts) || hosts < 1) {
    throw new ParseError(`host count must be a positive integer, got ${hosts}`);
  }
  if (hosts === 1) return 32;
  if (hosts === 2) return 31;
  for (let prefix = 30; prefix >= 0; prefix--) {
    if (2 ** (32 - prefix) - 2 >= hosts) return prefix;
  }
  throw new ParseError(`${hosts} hosts do not fit in IPv4`);
}

export interface VlsmRequest {
  name: string;
  hosts: number;
}

export interface VlsmAllocation extends VlsmRequest {
  subnet: Subnet;
}

/**
 * Variable-Length Subnet Masking: carve `parent` into blocks sized for each
 * request. Sorting largest-first keeps every block naturally aligned, so a
 * simple bump allocator never wastes space on alignment gaps.
 */
export function vlsm(parent: Subnet, requests: VlsmRequest[]): VlsmAllocation[] {
  const ordered = [...requests].sort((a, b) => b.hosts - a.hosts);
  let cursor = parent.network;
  const end = parent.broadcast;
  const out: VlsmAllocation[] = [];
  for (const req of ordered) {
    const prefix = prefixForHosts(req.hosts);
    if (prefix < parent.prefix) {
      throw new ParseError(`"${req.name}" needs a /${prefix}, larger than ${parent}`);
    }
    const subnet = new Subnet(cursor, prefix);
    if (subnet.network !== cursor || cursor > end || subnet.broadcast > end) {
      throw new ParseError(`${parent} has no room left for "${req.name}" (/${prefix})`);
    }
    out.push({ ...req, subnet });
    cursor = subnet.broadcast + 1;
  }
  return out;
}

/**
 * Route summarisation / aggregation: return the minimal set of CIDR blocks
 * covering exactly the same addresses as the input.
 *
 * Algorithm: convert to sorted, merged [start, end] intervals, then greedily
 * cover each interval with the largest aligned block that fits.
 */
export function summarize(subnets: Subnet[]): Subnet[] {
  const intervals = subnets
    .map((s) => [s.network, s.broadcast] as [number, number])
    .sort((a, b) => a[0] - b[0]);

  const merged: [number, number][] = [];
  for (const [start, end] of intervals) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1] + 1) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }

  const out: Subnet[] = [];
  for (const [start, end] of merged) {
    let cursor = start;
    while (cursor <= end) {
      // Largest block allowed by alignment of `cursor` ...
      let prefix = cursor === 0 ? 0 : 32 - trailingZeros(cursor);
      // ... shrunk until it no longer overruns the interval.
      while (cursor + 2 ** (32 - prefix) - 1 > end) prefix++;
      out.push(new Subnet(cursor, prefix));
      cursor += 2 ** (32 - prefix);
    }
  }
  return out;
}

function trailingZeros(value: number): number {
  if (value === 0) return 32;
  return 31 - Math.clz32(value & -value);
}
