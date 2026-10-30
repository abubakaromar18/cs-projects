import type { Metadata } from "next";
import Link from "next/link";
import { ProjectCard } from "@/components/ProjectCard";
import { allTech, filterProjects, projects } from "@/data/projects";

export const metadata: Metadata = { title: "Projects" };

// The filter lives in the URL (?tech=Go), so filtered views are shareable and
// work without client-side JavaScript.
export default async function ProjectsPage({ searchParams }: { searchParams: Promise<{ tech?: string }> }) {
  const { tech } = await searchParams;
  const shown = filterProjects(projects, tech);

  return (
    <>
      <h1>Projects</h1>
      <nav aria-label="Filter by technology" className="filters">
        <Link href="/projects" className="chip" aria-current={!tech ? "true" : undefined}>All</Link>
        {allTech().map((t) => (
          <Link key={t} href={`/projects?tech=${encodeURIComponent(t)}`} className="chip" aria-current={tech?.toLowerCase() === t.toLowerCase() ? "true" : undefined}>
            {t}
          </Link>
        ))}
      </nav>
      {shown.length === 0 ? (
        <p className="muted">No projects use “{tech}”.</p>
      ) : (
        <div className="grid">{shown.map((p) => <ProjectCard key={p.slug} project={p} />)}</div>
      )}
    </>
  );
}
