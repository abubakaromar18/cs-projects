/**
 * Minimal HTTP server built on node:http (no framework).
 *
 * Routes:
 *   GET  /               dashboard page (public/index.html)
 *   GET  /<asset>        static files from public/ and the compiled client (dist/client)
 *   GET  /api/status     current StatusSnapshot as JSON
 *   POST /api/refresh    run a check round now, then return the fresh snapshot
 *   GET  /api/health     liveness probe for the dashboard itself
 */
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Monitor } from "./monitor.js";

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".png": "image/png",
};

export interface AppOptions {
  /** Directory holding index.html and styles.css. */
  publicDir?: string;
  /** Directory holding the compiled browser JavaScript. */
  clientDir?: string;
}

const here = path.dirname(fileURLToPath(import.meta.url));

/**
 * Resolve `requestPath` inside `root`, refusing anything that escapes it
 * (e.g. "/../../etc/passwd"). Returns undefined for a traversal attempt.
 */
export function safeJoin(root: string, requestPath: string): string | undefined {
  let decoded: string;
  try {
    decoded = decodeURIComponent(requestPath);
  } catch {
    return undefined; // malformed %-encoding
  }
  if (decoded.includes("\0")) return undefined;
  const resolved = path.resolve(root, "." + path.posix.normalize("/" + decoded));
  const rootWithSep = path.resolve(root) + path.sep;
  return resolved.startsWith(rootWithSep) ? resolved : undefined;
}

export function createApp(monitor: Monitor, options: AppOptions = {}): http.Server {
  // Defaults assume the compiled layout: dist/server/app.js → ../../public, ../client
  const publicDir = options.publicDir ?? path.resolve(here, "../../public");
  const clientDir = options.clientDir ?? path.resolve(here, "../client");

  const sendJson = (res: http.ServerResponse, status: number, body: unknown) => {
    res.writeHead(status, { "content-type": MIME[".json"], "cache-control": "no-store" });
    res.end(JSON.stringify(body));
  };

  const sendFile = async (res: http.ServerResponse, roots: string[], reqPath: string): Promise<boolean> => {
    for (const root of roots) {
      const file = safeJoin(root, reqPath);
      if (!file) continue;
      try {
        const data = await readFile(file);
        res.writeHead(200, {
          "content-type": MIME[path.extname(file)] ?? "application/octet-stream",
          "x-content-type-options": "nosniff",
        });
        res.end(data);
        return true;
      } catch {
        // not in this root; try the next one
      }
    }
    return false;
  };

  return http.createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", "http://localhost");
    const method = req.method ?? "GET";

    try {
      if (url.pathname === "/api/health") {
        return sendJson(res, 200, { ok: true, rounds: monitor.completedRounds });
      }
      if (url.pathname === "/api/status") {
        if (method !== "GET") return sendJson(res, 405, { error: "method not allowed" });
        return sendJson(res, 200, monitor.snapshot());
      }
      if (url.pathname === "/api/refresh") {
        if (method !== "POST") return sendJson(res, 405, { error: "use POST" });
        await monitor.checkAll();
        return sendJson(res, 200, monitor.snapshot());
      }
      if (url.pathname.startsWith("/api/")) return sendJson(res, 404, { error: "not found" });

      if (method !== "GET" && method !== "HEAD") {
        res.writeHead(405).end();
        return;
      }
      const reqPath = url.pathname === "/" ? "/index.html" : url.pathname;
      if (await sendFile(res, [publicDir, clientDir], reqPath)) return;
      res.writeHead(404, { "content-type": "text/plain; charset=utf-8" }).end("Not found");
    } catch (err) {
      sendJson(res, 500, { error: (err as Error).message });
    }
  });
}
