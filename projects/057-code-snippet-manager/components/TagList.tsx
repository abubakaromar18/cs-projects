import Link from "next/link";

export function TagList({ tags }: { tags: string[] }) {
  return (
    <ul className="tags">
      {tags.map((t) => (
        <li key={t}>
          <Link href={`/?tag=${encodeURIComponent(t)}`} className="tag">
            #{t}
          </Link>
        </li>
      ))}
    </ul>
  );
}
