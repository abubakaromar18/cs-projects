import Link from "next/link";
import { notFound } from "next/navigation";
import { CodeBlock } from "@/components/CodeBlock";
import { CopyButton } from "@/components/CopyButton";
import { DeleteButton } from "@/components/DeleteButton";
import { TagList } from "@/components/TagList";
import { getStore } from "@/lib/store";

export const dynamic = "force-dynamic";

export default async function SnippetPage({ params }: { params: Promise<{ id: string }> }) {
  const snippet = await getStore().get((await params).id);
  if (!snippet) notFound();
  return (
    <article className="detail">
      <header>
        <h1>{snippet.title}</h1>
        <span className="lang">{snippet.language}</span>
      </header>
      {snippet.description && <p className="desc">{snippet.description}</p>}
      <TagList tags={snippet.tags} />
      <div className="actions">
        <CopyButton text={snippet.code} />
        <Link href={`/snippets/${snippet.id}/edit`} className="btn small">
          Edit
        </Link>
        <DeleteButton id={snippet.id} />
      </div>
      <CodeBlock code={snippet.code} language={snippet.language} />
      <p className="muted">Updated {new Date(snippet.updatedAt).toLocaleString("en-US")}</p>
    </article>
  );
}
