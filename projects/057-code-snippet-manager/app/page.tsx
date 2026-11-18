import { SnippetBrowser } from "@/components/SnippetBrowser";
import { getStore } from "@/lib/store";

// The data file changes at runtime, so never prerender this page.
export const dynamic = "force-dynamic";

type Search = Promise<Record<string, string | string[] | undefined>>;

const asArray = (v: string | string[] | undefined) => (v === undefined ? [] : Array.isArray(v) ? v : [v]);

export default async function Home({ searchParams }: { searchParams: Search }) {
  const sp = await searchParams;
  const snippets = await getStore().list();
  return (
    <SnippetBrowser
      snippets={snippets}
      initial={{
        q: asArray(sp.q)[0] ?? "",
        tags: asArray(sp.tag),
        language: asArray(sp.language)[0] ?? "",
      }}
    />
  );
}
