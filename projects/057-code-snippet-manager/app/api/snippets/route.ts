import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { search } from "@/lib/search";
import { validateSnippet } from "@/lib/validation";

/** GET /api/snippets?q=debounce&tag=git&tag=cli&language=bash */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const results = search(await getStore().list(), {
    query: url.searchParams.get("q") ?? undefined,
    tags: url.searchParams.getAll("tag"),
    language: url.searchParams.get("language") ?? undefined,
  });
  return NextResponse.json(results);
}

/** POST /api/snippets  { title, description?, language, code, tags? } */
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const result = validateSnippet(body);
  if (!result.ok) return NextResponse.json({ errors: result.errors }, { status: 400 });
  const snippet = await getStore().create(result.value);
  return NextResponse.json(snippet, { status: 201 });
}
