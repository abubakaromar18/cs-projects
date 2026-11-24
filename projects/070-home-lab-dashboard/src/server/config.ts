/**
 * Configuration loading and validation.
 *
 * The config file is user-written JSON, so it is treated as untrusted input:
 * every field is checked, defaults are filled in, and errors name the exact
 * path ("groups[1].services[0].url") so mistakes are easy to fix.
 */
import { readFile } from "node:fs/promises";
import type { CheckSpec, DashboardConfig, ServiceConfig } from "../shared/types.js";

export class ConfigError extends Error {
  constructor(public readonly errors: string[]) {
    super(`Invalid dashboard config:\n  - ${errors.join("\n  - ")}`);
    this.name = "ConfigError";
  }
}

const DEFAULT_TIMEOUT_MS = 5000;
const DEFAULT_SLOW_MS = 1500;

type Json = unknown;
const isObject = (v: Json): v is Record<string, Json> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

/** Turn "Pi-hole (DNS)" into "pi-hole-dns". */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}

/**
 * Validate a parsed JSON value and produce a normalised `DashboardConfig`.
 * All problems are collected before throwing, rather than failing on the first.
 */
export function parseConfig(raw: Json): DashboardConfig {
  const errors: string[] = [];
  if (!isObject(raw)) throw new ConfigError(["config must be a JSON object"]);

  const title = optionalString(raw, "title", "title", errors) ?? "Home Lab";
  const intervalSeconds = optionalNumber(raw, "intervalSeconds", "intervalSeconds", errors, 1, 86400) ?? 30;
  const historySize = optionalNumber(raw, "historySize", "historySize", errors, 1, 10000) ?? 60;

  const services: ServiceConfig[] = [];
  const seenIds = new Set<string>();

  if (!Array.isArray(raw.groups) || raw.groups.length === 0) {
    errors.push("groups: must be a non-empty array");
  } else {
    raw.groups.forEach((g, gi) => {
      const gPath = `groups[${gi}]`;
      if (!isObject(g)) return void errors.push(`${gPath}: must be an object`);
      const groupName = requiredString(g, "name", `${gPath}.name`, errors);
      if (!Array.isArray(g.services)) return void errors.push(`${gPath}.services: must be an array`);

      g.services.forEach((s, si) => {
        const sPath = `${gPath}.services[${si}]`;
        if (!isObject(s)) return void errors.push(`${sPath}: must be an object`);
        const name = requiredString(s, "name", `${sPath}.name`, errors);
        const url = requiredString(s, "url", `${sPath}.url`, errors);
        let parsedUrl: URL | undefined;
        if (url !== undefined) {
          try {
            parsedUrl = new URL(url);
          } catch {
            errors.push(`${sPath}.url: "${url}" is not a valid URL`);
          }
        }
        const icon = optionalString(s, "icon", `${sPath}.icon`, errors);
        const description = optionalString(s, "description", `${sPath}.description`, errors);
        const check = parseCheck(s.check, parsedUrl, `${sPath}.check`, errors);

        if (groupName === undefined || name === undefined || url === undefined || check === undefined) return;
        let id = slugify(`${groupName}-${name}`) || `service-${services.length}`;
        // Two services with the same name in the same group get a numeric suffix.
        for (let n = 2; seenIds.has(id); n++) id = `${slugify(`${groupName}-${name}`)}-${n}`;
        seenIds.add(id);
        services.push({ id, name, url, group: groupName, icon, description, check });
      });
    });
  }

  if (errors.length > 0) throw new ConfigError(errors);
  return { title, intervalSeconds, historySize, services };
}

/**
 * Work out the health check for a service. When `check` is omitted, HTTP(S)
 * URLs get an HTTP check and anything else (ssh://, smb://…) gets none.
 */
function parseCheck(raw: Json, url: URL | undefined, path: string, errors: string[]): CheckSpec | undefined {
  const isHttpUrl = url !== undefined && (url.protocol === "http:" || url.protocol === "https:");
  if (raw === undefined) {
    return isHttpUrl
      ? { type: "http", timeoutMs: DEFAULT_TIMEOUT_MS, slowMs: DEFAULT_SLOW_MS }
      : { type: "none" };
  }
  if (!isObject(raw)) return void errors.push(`${path}: must be an object`);

  const timeoutMs = optionalNumber(raw, "timeoutMs", `${path}.timeoutMs`, errors, 1, 120000) ?? DEFAULT_TIMEOUT_MS;
  const slowMs = optionalNumber(raw, "slowMs", `${path}.slowMs`, errors, 1, 120000) ?? DEFAULT_SLOW_MS;

  switch (raw.type) {
    case "none":
      return { type: "none" };
    case "http": {
      const target = optionalString(raw, "target", `${path}.target`, errors);
      const checkPath = optionalString(raw, "path", `${path}.path`, errors);
      if (target === undefined && !isHttpUrl) {
        errors.push(`${path}: http check needs an http(s) service url or a "target"`);
      }
      let expectStatus: number[] | undefined;
      if (raw.expectStatus !== undefined) {
        if (
          !Array.isArray(raw.expectStatus) ||
          raw.expectStatus.length === 0 ||
          !raw.expectStatus.every((c) => Number.isInteger(c) && (c as number) >= 100 && (c as number) <= 599)
        ) {
          errors.push(`${path}.expectStatus: must be a non-empty array of HTTP status codes`);
        } else {
          expectStatus = raw.expectStatus as number[];
        }
      }
      if (raw.insecure !== undefined && typeof raw.insecure !== "boolean") {
        errors.push(`${path}.insecure: must be true or false`);
      }
      return { type: "http", target, path: checkPath, expectStatus, insecure: raw.insecure === true, timeoutMs, slowMs };
    }
    case "tcp": {
      // Host and port default to the service URL's host/port where possible.
      const host = optionalString(raw, "host", `${path}.host`, errors) ?? url?.hostname;
      const port = optionalNumber(raw, "port", `${path}.port`, errors, 1, 65535) ?? (url?.port ? Number(url.port) : undefined);
      if (!host) errors.push(`${path}.host: required for tcp checks`);
      if (port === undefined) errors.push(`${path}.port: required for tcp checks (the url has no port)`);
      if (!host || port === undefined) return undefined;
      return { type: "tcp", host, port, timeoutMs, slowMs };
    }
    default:
      errors.push(`${path}.type: must be "http", "tcp" or "none"`);
      return undefined;
  }
}

function requiredString(obj: Record<string, Json>, key: string, path: string, errors: string[]): string | undefined {
  const v = obj[key];
  if (typeof v !== "string" || v.trim() === "") {
    errors.push(`${path}: required non-empty string`);
    return undefined;
  }
  return v.trim();
}

function optionalString(obj: Record<string, Json>, key: string, path: string, errors: string[]): string | undefined {
  const v = obj[key];
  if (v === undefined) return undefined;
  if (typeof v !== "string") {
    errors.push(`${path}: must be a string`);
    return undefined;
  }
  return v;
}

function optionalNumber(
  obj: Record<string, Json>, key: string, path: string, errors: string[], min: number, max: number,
): number | undefined {
  const v = obj[key];
  if (v === undefined) return undefined;
  if (typeof v !== "number" || !Number.isFinite(v) || v < min || v > max) {
    errors.push(`${path}: must be a number between ${min} and ${max}`);
    return undefined;
  }
  return v;
}

/** Read and validate a config file from disk. */
export async function loadConfig(file: string): Promise<DashboardConfig> {
  const text = await readFile(file, "utf8");
  let json: Json;
  try {
    json = JSON.parse(text);
  } catch (err) {
    throw new ConfigError([`${file}: not valid JSON (${(err as Error).message})`]);
  }
  return parseConfig(json);
}
