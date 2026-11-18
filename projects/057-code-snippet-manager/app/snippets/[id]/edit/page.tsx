import { notFound } from "next/navigation";
import { SnippetForm } from "@/components/SnippetForm";
import { getStore } from "@/lib/store";

export const dynamic = "force-dynamic";

export default async function EditSnippet({ params }: { params: Promise<{ id: string }> }) {
  const snippet = await getStore().get((await params).id);
  if (!snippet) notFound();
  return (
    <>
      <h1>Edit snippet</h1>
      <SnippetForm snippet={snippet} />
    </>
  );
}
