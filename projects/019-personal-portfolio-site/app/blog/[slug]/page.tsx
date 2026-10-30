import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { formatDate, getAllPosts, getPostBySlug } from "@/lib/posts";

type Params = { params: Promise<{ slug: string }> };

// Pre-render every post at build time (Static Site Generation).
export function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

// Unknown slugs 404 instead of being rendered on demand.
export const dynamicParams = false;

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const post = getPostBySlug((await params).slug);
  return post ? { title: post.title, description: post.summary } : {};
}

export default async function PostPage({ params }: Params) {
  const post = getPostBySlug((await params).slug);
  if (!post) notFound();

  return (
    <article className="post">
      <p><Link href="/blog">← All posts</Link></p>
      <h1>{post.title}</h1>
      <p className="muted">
        <time dateTime={post.date}>{formatDate(post.date)}</time> · {post.readingMinutes} min read
        {post.tags.length > 0 && <> · {post.tags.map((t) => `#${t}`).join(" ")}</>}
      </p>
      {/* Safe: renderMarkdown escapes all text and filters link schemes. */}
      <div className="prose" dangerouslySetInnerHTML={{ __html: post.html }} />
    </article>
  );
}
