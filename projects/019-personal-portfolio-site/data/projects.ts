export interface Project {
  slug: string;
  title: string;
  description: string;
  tech: string[];
  repo?: string;
  demo?: string;
  featured: boolean;
  year: number;
}

export const projects: Project[] = [
  {
    slug: "url-shortener",
    title: "URL Shortener",
    description: "Base62 short links backed by a SQL store, with click analytics and expiry.",
    tech: ["Go", "SQLite", "REST"],
    repo: "https://github.com/",
    featured: true,
    year: 2026,
  },
  {
    slug: "sorting-visualizer",
    title: "Sorting Visualizer",
    description: "Step-by-step animations of eight sorting algorithms with comparison counters.",
    tech: ["TypeScript", "Canvas"],
    repo: "https://github.com/",
    demo: "https://example.com/",
    featured: true,
    year: 2026,
  },
  {
    slug: "logic-gate-simulator",
    title: "Logic Gate Simulator",
    description: "Drag-and-drop digital circuits: adders, latches and auto-generated truth tables.",
    tech: ["TypeScript", "SVG"],
    repo: "https://github.com/",
    featured: true,
    year: 2026,
  },
  {
    slug: "tic-tac-toe-minimax",
    title: "Tic-Tac-Toe with Minimax",
    description: "An unbeatable opponent using minimax with alpha-beta pruning.",
    tech: ["Java"],
    repo: "https://github.com/",
    featured: false,
    year: 2025,
  },
  {
    slug: "bank-account-actors",
    title: "Bank Account Actors",
    description: "Concurrent accounts modelled as supervised processes on the BEAM.",
    tech: ["Elixir", "OTP"],
    repo: "https://github.com/",
    featured: false,
    year: 2025,
  },
];

/** Every distinct technology, alphabetised — used for the filter chips. */
export function allTech(list: Project[] = projects): string[] {
  return [...new Set(list.flatMap((p) => p.tech))].sort((a, b) => a.localeCompare(b));
}

/** Filter by technology (case-insensitive); an empty/undefined filter returns all, newest first. */
export function filterProjects(list: Project[], tech?: string): Project[] {
  const t = tech?.trim().toLowerCase();
  return list
    .filter((p) => !t || p.tech.some((x) => x.toLowerCase() === t))
    .sort((a, b) => b.year - a.year || a.title.localeCompare(b.title));
}
