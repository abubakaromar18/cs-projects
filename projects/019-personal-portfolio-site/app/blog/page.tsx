import type { Metadata } from "next";
import { PostList } from "@/components/PostList";
import { getAllPosts } from "@/lib/posts";

export const metadata: Metadata = { title: "Blog" };

export default function BlogPage() {
  return (
    <>
      <h1>Blog</h1>
      <p className="muted">Notes on things I&apos;ve built and learned.</p>
      <PostList posts={getAllPosts()} />
    </>
  );
}
