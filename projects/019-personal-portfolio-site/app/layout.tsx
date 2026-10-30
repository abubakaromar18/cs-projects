import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";
import { site } from "@/data/site";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: `${site.name} — ${site.role}`, template: `%s · ${site.name}` },
  description: site.tagline,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <Nav name={site.name} />
        <main id="main" className="container">
          {children}
        </main>
        <footer className="site-footer container muted">
          © {new Date().getFullYear()} {site.name} ·{" "}
          {site.links.map((l, i) => (
            <span key={l.href}>
              {i > 0 && " · "}
              <a href={l.href} target="_blank" rel="noopener noreferrer">
                {l.label}
              </a>
            </span>
          ))}
        </footer>
      </body>
    </html>
  );
}
