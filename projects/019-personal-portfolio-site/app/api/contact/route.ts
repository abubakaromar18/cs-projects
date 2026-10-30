import { NextResponse, type NextRequest } from "next/server";
import { handleContact } from "@/lib/contactHandler";
import { InMemoryMessageStore } from "@/lib/messageStore";
import { SlidingWindowRateLimiter } from "@/lib/rateLimit";

// Module-level singletons live for the lifetime of the server process.
const limiter = new SlidingWindowRateLimiter(5, 10 * 60 * 1000); // 5 messages / 10 min / IP
const store = new InMemoryMessageStore();

const MAX_BODY_BYTES = 10_000;

function clientKey(req: NextRequest): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || req.headers.get("x-real-ip") || "local";
}

export async function POST(req: NextRequest) {
  const raw = await req.text();
  if (raw.length > MAX_BODY_BYTES) {
    return NextResponse.json({ ok: false, error: "Message too large." }, { status: 413 });
  }

  limiter.sweep();
  const res = await handleContact(clientKey(req), raw, { limiter, store });
  if (res.status === 201) {
    // Replace with an email/DB integration in production.
    console.log("[contact] new message", res.body.id);
  }
  return NextResponse.json(res.body, { status: res.status, headers: res.headers });
}
