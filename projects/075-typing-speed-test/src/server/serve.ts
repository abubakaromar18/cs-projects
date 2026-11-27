/**
 * Minimal static file server for local development: serves public/ at "/"
 * and the compiled browser modules from dist/ at "/dist/". Binds to
 * 127.0.0.1 by default and refuses any path that escapes its roots.
 */
import { createServer, type Server } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".map": "application/json",
};

/** Resolve a URL path under root, or null if it would escape root. */
export function safeResolve(root: string, urlPath: string): string | null {
  let decoded: string;
  try {
    decoded = decodeURIComponent(urlPath);
  } catch {
    return null;
  }
  if (decoded.includes("\0")) return null;
  const rootAbs = resolve(root);
  const full = resolve(rootAbs, "." + normalize("/" + decoded));
  return full === rootAbs || full.startsWith(rootAbs + sep) ? full : null;
}

export interface ServeOptions {
  publicDir: string;
  distDir: string;
}

export function makeServer(opts: ServeOptions): Server {
  return createServer(async (req, res) => {
    if (req.method !== "GET" && req.method !== "HEAD") {
      res.writeHead(405, { Allow: "GET, HEAD" }).end();
      return;
    }
    const path = new URL(req.url ?? "/", "http://localhost").pathname;
    const [root, rel] = path.startsWith("/dist/")
      ? [opts.distDir, path.slice("/dist".length)]
      : [opts.publicDir, path === "/" ? "/index.html" : path];
    const file = safeResolve(root, rel);
    if (!file) {
      res.writeHead(400).end("bad path");
      return;
    }
    try {
      if (!(await stat(file)).isFile()) throw new Error("not a file");
      const body = await readFile(file);
      res.writeHead(200, {
        "Content-Type": MIME[extname(file)] ?? "application/octet-stream",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      });
      res.end(req.method === "HEAD" ? undefined : body);
    } catch {
      res.writeHead(404, { "Content-Type": "text/plain" }).end("not found");
    }
  });
}

// Run directly: node dist/server/serve.js [--port N]
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const here = fileURLToPath(new URL(".", import.meta.url)); // dist/server/
  const projectRoot = join(here, "..", "..");
  const portArg = process.argv.indexOf("--port");
  const port = portArg > 0 ? Number(process.argv[portArg + 1]) : Number(process.env.PORT ?? 5175);
  makeServer({ publicDir: join(projectRoot, "public"), distDir: join(projectRoot, "dist") })
    .listen(port, "127.0.0.1", () => console.log(`Typing test running at http://127.0.0.1:${port}/`));
}
