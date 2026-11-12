/**
 * Low-level IPv4 address arithmetic.
 *
 * An IPv4 address is just a 32-bit unsigned integer. JavaScript bitwise
 * operators work on *signed* 32-bit values, so every result that might set
 * the top bit is normalised back to unsigned with `>>> 0`.
 */

export const MAX_IP = 0xffffffff;

/** Error thrown for any malformed address, prefix or mask. */
export class ParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ParseError";
  }
}

/** Parse dotted-quad notation ("192.168.1.10") into a uint32. */
export function parseIp(text: string): number {
  const parts = text.trim().split(".");
  if (parts.length !== 4) {
    throw new ParseError(`"${text}" is not a dotted-quad IPv4 address`);
  }
  let value = 0;
  for (const part of parts) {
    // Reject empty octets, signs, hex, and leading zeros ("010" is ambiguous:
    // some libc parsers treat it as octal).
    if (!/^(0|[1-9]\d{0,2})$/.test(part)) {
      throw new ParseError(`invalid octet "${part}" in "${text}"`);
    }
    const octet = Number(part);
    if (octet > 255) {
      throw new ParseError(`octet ${octet} out of range in "${text}"`);
    }
    value = value * 256 + octet; // multiplication avoids signed-shift overflow
  }
  return value;
}

/** Format a uint32 as dotted-quad notation. */
export function formatIp(value: number): string {
  return [24, 16, 8, 0].map((shift) => (value >>> shift) & 0xff).join(".");
}

/** Netmask for a prefix length, e.g. 24 → 0xffffff00. */
export function prefixToMask(prefix: number): number {
  assertPrefix(prefix);
  // `<< 32` is a no-op in JS (shift count is taken mod 32), so /0 is special.
  return prefix === 0 ? 0 : (MAX_IP << (32 - prefix)) >>> 0;
}

/** Inverse of {@link prefixToMask}; rejects non-contiguous masks. */
export function maskToPrefix(mask: number): number {
  const inverted = ~mask >>> 0;
  // A valid mask's inverse is 2^k - 1, so (inv & (inv + 1)) must be zero.
  if ((inverted & (inverted + 1)) !== 0) {
    throw new ParseError(`${formatIp(mask)} is not a contiguous netmask`);
  }
  return 32 - popcount(inverted);
}

/** Number of set bits in a 32-bit value (SWAR / Hamming weight trick). */
export function popcount(value: number): number {
  let v = value >>> 0;
  v = v - ((v >>> 1) & 0x55555555);
  v = (v & 0x33333333) + ((v >>> 2) & 0x33333333);
  v = (v + (v >>> 4)) & 0x0f0f0f0f;
  return Math.imul(v, 0x01010101) >>> 24;
}

/** 32-character binary string, most significant bit first. */
export function toBinary(value: number): string {
  return (value >>> 0).toString(2).padStart(32, "0");
}

export function assertPrefix(prefix: number): void {
  if (!Number.isInteger(prefix) || prefix < 0 || prefix > 32) {
    throw new ParseError(`prefix length must be an integer 0-32, got ${prefix}`);
  }
}

/** Address class from the historical classful scheme (RFC 791). */
export function addressClass(ip: number): "A" | "B" | "C" | "D" | "E" {
  const first = ip >>> 24;
  if (first < 128) return "A";
  if (first < 192) return "B";
  if (first < 224) return "C";
  if (first < 240) return "D";
  return "E";
}

interface SpecialRange {
  base: number;
  prefix: number;
  label: string;
}

// Well-known special-purpose blocks (RFC 6890 and friends). Order matters:
// the most specific match is chosen.
const SPECIAL_RANGES: SpecialRange[] = [
  ["0.0.0.0", 8, "\"This network\" (RFC 791)"],
  ["10.0.0.0", 8, "Private (RFC 1918)"],
  ["100.64.0.0", 10, "Carrier-grade NAT (RFC 6598)"],
  ["127.0.0.0", 8, "Loopback (RFC 1122)"],
  ["169.254.0.0", 16, "Link-local (RFC 3927)"],
  ["172.16.0.0", 12, "Private (RFC 1918)"],
  ["192.0.2.0", 24, "Documentation TEST-NET-1 (RFC 5737)"],
  ["192.168.0.0", 16, "Private (RFC 1918)"],
  ["198.18.0.0", 15, "Benchmarking (RFC 2544)"],
  ["198.51.100.0", 24, "Documentation TEST-NET-2 (RFC 5737)"],
  ["203.0.113.0", 24, "Documentation TEST-NET-3 (RFC 5737)"],
  ["224.0.0.0", 4, "Multicast (RFC 5771)"],
  ["240.0.0.0", 4, "Reserved (RFC 1112)"],
  ["255.255.255.255", 32, "Limited broadcast (RFC 919)"],
].map(([ip, prefix, label]) => ({
  base: parseIp(ip as string),
  prefix: prefix as number,
  label: label as string,
}));

/** Describe the special-purpose block an address falls in, or "Public". */
export function addressScope(ip: number): string {
  let best: SpecialRange | undefined;
  for (const range of SPECIAL_RANGES) {
    const mask = prefixToMask(range.prefix);
    if (((ip & mask) >>> 0) === range.base && (!best || range.prefix > best.prefix)) {
      best = range;
    }
  }
  return best ? best.label : "Public";
}
