#!/usr/bin/env node
/**
 * CLI entry point.
 *
 *   node dist/server/main.js [--config services.json] [--port 8080] [--host 127.0.0.1] [--once]
 *
 * --once runs a single check round, prints a table and exits with status 1 if
 * anything is down, which makes it usable from cron or CI.
 */
import { realpathSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";
import { createApp } from "./app.js";
import { ConfigError, loadConfig } from "./config.js";
import { Monitor } from "./monitor.js";
import type { StatusSnapshot } from "../shared/types.js";

const SYMBOL = { up: "●", degraded: "◐", down: "○", unknown: "·" } as const;

/** Render a snapshot as a plain-text table for the terminal. */
export function formatTable(snap: StatusSnapshot): string {
  const rows = snap.services.map((s) => [
    `${SYMBOL[s.current.health]} ${s.current.health}`,
    s.group,
    s.name,
    s.current.latencyMs !== undefined ? `${s.current.latencyMs} ms` : "-",
    s.current.detail,
  ]);
  const header = ["STATUS", "GROUP", "SERVICE", "LATENCY", "DETAIL"];
  const widths = header.map((h, i) => Math.max(h.length, ...rows.map((r) => r[i].length)));
  const line = (cols: string[]) => cols.map((c, i) => c.padEnd(widths[i])).join("  ").trimEnd();
  const { up, degraded, down, unknown } = snap.summary;
  return [
    snap.title,
    line(header),
    ...rows.map(line),
    "",
    `${up} up, ${degraded} degraded, ${down} down, ${unknown} unchecked`,
  ].join("\n");
}

async function main(): Promise<void> {
  const { values } = parseArgs({
    options: {
      config: { type: "string", short: "c", default: "services.json" },
      port: { type: "string", short: "p", default: process.env.PORT ?? "8080" },
      // Loopback by default: exposing a map of your network should be a deliberate choice.
      host: { type: "string", default: process.env.HOST ?? "127.0.0.1" },
      once: { type: "boolean", default: false },
      help: { type: "boolean", short: "h", default: false },
    },
  });

  if (values.help) {
    console.log("Usage: homelab-dashboard [--config services.json] [--port 8080] [--host 127.0.0.1] [--once]");
    return;
  }

  const config = await loadConfig(values.config!);
  const monitor = new Monitor(config);

  if (values.once) {
    await monitor.checkAll();
    const snap = monitor.snapshot();
    console.log(formatTable(snap));
    process.exitCode = snap.summary.down > 0 ? 1 : 0;
    return;
  }

  const port = Number(values.port);
  const server = createApp(monitor);
  server.listen(port, values.host, () => {
    console.log(`${config.title}: ${config.services.length} services, checking every ${config.intervalSeconds}s`);
    console.log(`Dashboard on http://${values.host}:${port}`);
  });
  monitor.start();

  const shutdown = () => {
    monitor.stop();
    server.close(() => process.exit(0));
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

// Only run when executed directly, not when imported by tests.
if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  main().catch((err) => {
    console.error(err instanceof ConfigError ? err.message : err);
    process.exit(2);
  });
}
