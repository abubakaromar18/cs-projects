import type { Metadata } from "next";
import { ContactForm } from "@/components/ContactForm";
import { site } from "@/data/site";

export const metadata: Metadata = { title: "Contact" };

export default function ContactPage() {
  return (
    <>
      <h1>Contact</h1>
      <p className="muted">
        Have a question or an opportunity? Send a message, or email{" "}
        <a href={`mailto:${site.email}`}>{site.email}</a>.
      </p>
      <ContactForm />
    </>
  );
}
