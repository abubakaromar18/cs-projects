import Link from "next/link";
import { ProjectCard } from "@/components/ProjectCard";
import { PostList } from "@/components/PostList";
import { projects } from "@/data/projects";
import { site } from "@/data/site";
import { getAllPosts } from "@/lib/posts";

export default function HomePage() {
  const featured = projects.filter((p) => p.featured);
  const recent = getAllPosts().slice(0, 3);

  return (
    <>
      <section className="hero">
        <p className="eyebrow">{site.role} · {site.location}</p>
        <h1>Hi, I&apos;m {site.name}.</h1>
        <p className="lead">{site.tagline}</p>
        <div className="actions">
          <Link href="/projects" className="button">See my work</Link>
          <Link href="/contact" className="button secondary">Get in touch</Link>
        </div>
        <ul className="chips" aria-label="Skills">
          {site.skills.map((s) => <li key={s} className="chip">{s}</li>)}
        </ul>
      </section>

      <section>
        <div className="section-head">
          <h2>Featured projects</h2>
          <Link href="/projects">All projects →</Link>
        </div>
        <div className="grid">
          {featured.map((p) => <ProjectCard key={p.slug} project={p} />)}
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Recent writing</h2>
          <Link href="/blog">All posts →</Link>
        </div>
        <PostList posts={recent} />
      </section>
    </>
  );
}
