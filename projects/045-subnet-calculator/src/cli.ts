#!/usr/bin/env node
/**
 * Command-line entry point.
 *
 *   subnet <cidr>                       describe a block with bit breakdown
 *   subnet split <cidr> <newPrefix>     split into equal subnets
 *   subnet vlsm <cidr> name:hosts ...   allocate variable-size subnets
 *   subnet summarize <cidr> <cidr> ...  aggregate into minimal CIDR set
 *   subnet contains <cidr> <ip>         membership test
 */
import { realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ParseError, parseIp } from "./ipv4.js";
import { COLOR, PLAIN, renderReport, renderSplit, renderVlsm } from "./render.js";
import { Subnet, describe, summarize, vlsm } from "./subnet.js";

const USAGE = `Usage:
  subnet <ip>[/prefix | mask]           Describe a subnet (e.g. 192.168.10.77/26)
  subnet split <cidr> <newPrefix>       Split into equal subnets
  subnet vlsm <cidr> <name:hosts>...    VLSM plan (e.g. lan:100 wifi:50 p2p:2)
  subnet summarize <cidr>...            Aggregate routes into minimal CIDR set
  subnet contains <cidr> <ip>           Check whether an IP is inside a subnet

Options:
  --json        Machine-readable output (describe only)
  --no-color    Disable ANSI colors`;

/** Run the CLI; returns the process exit code. Output goes through `write`. */
export function run(argv: string[], write: (s: string) => void, color = false): number {
  const flags = new Set(argv.filter((a) => a.startsWith("--")));
  const args = argv.filter((a) => !a.startsWith("--"));
  const style = color && !flags.has("--no-color") ? COLOR : PLAIN;

  if (args.length === 0 || flags.has("--help")) {
    write(USAGE);
    return args.length === 0 && !flags.has("--help") ? 1 : 0;
  }

  try {
    const [cmd, ...rest] = args;
    switch (cmd) {
      case "split": {
        if (rest.length !== 2) throw new ParseError("split needs <cidr> <newPrefix>");
        const parent = Subnet.parse(rest[0]!);
        const newPrefix = Number(rest[1]!.replace(/^\//, ""));
        write(renderSplit(parent, parent.split(newPrefix)));
        return 0;
      }
      case "vlsm": {
        if (rest.length < 2) throw new ParseError("vlsm needs <cidr> and at least one name:hosts");
        const parent = Subnet.parse(rest[0]!);
        const requests = rest.slice(1).map((spec) => {
          const m = /^([^:]+):(\d+)$/.exec(spec);
          if (!m) throw new ParseError(`expected name:hosts, got "${spec}"`);
          return { name: m[1]!, hosts: Number(m[2]) };
        });
        write(renderVlsm(parent, vlsm(parent, requests)));
        return 0;
      }
      case "summarize": {
        if (rest.length === 0) throw new ParseError("summarize needs at least one CIDR");
        const result = summarize(rest.map((r) => Subnet.parse(r)));
        write(result.map(String).join("\n"));
        return 0;
      }
      case "contains": {
        if (rest.length !== 2) throw new ParseError("contains needs <cidr> <ip>");
        const subnet = Subnet.parse(rest[0]!);
        const inside = subnet.contains(parseIp(rest[1]!));
        write(`${rest[1]} is ${inside ? "inside" : "NOT inside"} ${subnet}`);
        return inside ? 0 : 2;
      }
      default: {
        // Allow "subnet 10.0.0.1 255.255.255.0" as two separate args.
        const report = describe(args.join(" "));
        write(flags.has("--json") ? JSON.stringify(report, null, 2) : renderReport(report, style));
        return 0;
      }
    }
  } catch (err) {
    if (err instanceof ParseError) {
      write(`error: ${err.message}`);
      return 1;
    }
    throw err;
  }
}

// Only execute when invoked directly, not when imported by tests.
function invokedDirectly(): boolean {
  if (!process.argv[1]) return false;
  try {
    // realpath resolves the symlink npm creates for the "subnet" bin.
    return realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
  } catch {
    return false;
  }
}

if (invokedDirectly()) {
  const code = run(process.argv.slice(2), (s) => console.log(s), Boolean(process.stdout.isTTY));
  process.exitCode = code;
}
