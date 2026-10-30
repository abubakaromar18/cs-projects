import type { Project } from "@/data/projects";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <article className="card">
      <div className="card-head">
        <h3>{project.title}</h3>
        <span className="muted">{project.year}</span>
      </div>
      <p>{project.description}</p>
      <ul className="chips" aria-label="Technologies">
        {project.tech.map((t) => (
          <li key={t} className="chip">
            {t}
          </li>
        ))}
      </ul>
      <div className="card-links">
        {project.repo && (
          <a href={project.repo} target="_blank" rel="noopener noreferrer">
            Source ↗
          </a>
        )}
        {project.demo && (
          <a href={project.demo} target="_blank" rel="noopener noreferrer">
            Live demo ↗
          </a>
        )}
      </div>
    </article>
  );
}
