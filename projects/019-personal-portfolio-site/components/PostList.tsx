import Link from "next/link";
import { formatDate, type PostMeta } from "@/lib/posts";

export function PostList({ posts }: { posts: PostMeta[] }) {
  if (posts.length === 0) return <p className="muted">No posts yet.</p>;
  return (
    <ul className="post-list">
      {posts.map((p) => (
        <li key={p.slug}>
          <Link href={`/blog/${p.slug}`}>
            <h3>{p.title}</h3>
          </Link>
          <p className="muted">
            <time dateTime={p.date}>{formatDate(p.date)}</time> · {p.readingMinutes} min read
          </p>
          {p.summary && <p>{p.summary}</p>}
        </li>
      ))}
    </ul>
  );
}
