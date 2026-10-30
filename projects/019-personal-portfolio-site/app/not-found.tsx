import Link from "next/link";

export default function NotFound() {
  return (
    <section className="hero">
      <h1>404 — Page not found</h1>
      <p className="lead">That page doesn&apos;t exist (yet).</p>
      <Link href="/" className="button">Go home</Link>
    </section>
  );
}
