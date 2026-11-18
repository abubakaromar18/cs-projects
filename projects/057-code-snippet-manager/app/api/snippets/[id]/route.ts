import { NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { validateSnippet } from "@/lib/validation";

type Ctx = { params: Promise<{ id: string }> };

const notFound = () => NextResponse.json({ error: "Snippet not found" }, { status: 404 });

export async function GET(_req: Request, { params }: Ctx) {
  const snippet = await getStore().get((await params).id);
  return snippet ? NextResponse.json(snippet) : notFound();
}

export async function PUT(req: Request, { params }: Ctx) {
  const result = validateSnippet(await req.json().catch(() => null));
  if (!result.ok) return NextResponse.json({ errors: result.errors }, { status: 400 });
  const snippet = await getStore().update((await params).id, result.value);
  return snippet ? NextResponse.json(snippet) : notFound();
}

export async function DELETE(_req: Request, { params }: Ctx) {
  const removed = await getStore().remove((await params).id);
  return removed ? new NextResponse(null, { status: 204 }) : notFound();
}
