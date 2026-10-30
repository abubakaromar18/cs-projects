import { describe, expect, it } from "vitest";
import { allTech, filterProjects, projects } from "@/data/projects";

describe("projects data", () => {
  it("has unique slugs", () => {
    const slugs = projects.map((p) => p.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("allTech is unique and sorted", () => {
    const t = allTech();
    expect(new Set(t).size).toBe(t.length);
    expect([...t].sort((a, b) => a.localeCompare(b))).toEqual(t);
  });

  it("filters case-insensitively and sorts newest first", () => {
    const ts = filterProjects(projects, "typescript");
    expect(ts.length).toBeGreaterThan(0);
    expect(ts.every((p) => p.tech.includes("TypeScript"))).toBe(true);
    const all = filterProjects(projects);
    expect(all).toHaveLength(projects.length);
    expect(all.map((p) => p.year)).toEqual([...all.map((p) => p.year)].sort((a, b) => b - a));
    expect(filterProjects(projects, "COBOL")).toEqual([]);
  });
});
