import { SlidingWindowRateLimiter } from "./rateLimit";
import type { MessageStore } from "./messageStore";
import { validateContact } from "./validation";

/**
 * Framework-agnostic core of POST /api/contact. The Next.js route is a thin
 * adapter around this, which lets the tests exercise the full request flow
 * (rate limit → parse → validate → honeypot → store) without a running server.
 */
export interface HandlerDeps {
  limiter: SlidingWindowRateLimiter;
  store: MessageStore;
}

export interface HandlerResponse {
  status: number;
  body: Record<string, unknown>;
  headers?: Record<string, string>;
}

export async function handleContact(clientKey: string, rawBody: string, deps: HandlerDeps): Promise<HandlerResponse> {
  const rl = deps.limiter.check(clientKey);
  if (!rl.allowed) {
    return {
      status: 429,
      body: { ok: false, error: "Too many messages. Please try again later." },
      headers: { "Retry-After": String(Math.ceil(rl.retryAfterMs / 1000)) },
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(rawBody);
  } catch {
    return { status: 400, body: { ok: false, error: "Request body must be JSON." } };
  }

  const result = validateContact(parsed);
  if (!result.ok) {
    return { status: 422, body: { ok: false, errors: result.errors } };
  }

  // Pretend success to bots so they don't learn to avoid the honeypot.
  if (result.isSpam) {
    return { status: 200, body: { ok: true } };
  }

  const saved = await deps.store.save(result.value);
  return { status: 201, body: { ok: true, id: saved.id } };
}
