import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Snippets",
  description: "A personal code snippet manager with tags, search, and syntax highlighting",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <Link href="/" className="brand">
            {"</>"} Snippets
          </Link>
          <Link href="/new" className="btn primary small">
            New snippet
          </Link>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
