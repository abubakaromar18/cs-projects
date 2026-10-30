"use client";

import { useState, type FormEvent } from "react";
import { LIMITS, validateContact, type FieldErrors } from "@/lib/validation";

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "sent" } | { kind: "error"; message: string };

export function ContactForm() {
  const [errors, setErrors] = useState<FieldErrors>({});
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());

    // Same rules as the server, for instant feedback.
    const local = validateContact(payload);
    if (!local.ok) {
      setErrors(local.errors);
      return;
    }
    setErrors({});
    setStatus({ kind: "sending" });

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = (await res.json()) as { ok: boolean; error?: string; errors?: FieldErrors };
      if (res.ok && data.ok) {
        setStatus({ kind: "sent" });
        form.reset();
      } else {
        if (data.errors) setErrors(data.errors);
        setStatus({ kind: "error", message: data.error ?? "Please fix the errors above." });
      }
    } catch {
      setStatus({ kind: "error", message: "Network error — please try again." });
    }
  }

  if (status.kind === "sent") {
    return (
      <p role="status" className="success">
        Thanks! Your message was sent — I&apos;ll get back to you soon.
      </p>
    );
  }

  return (
    <form className="contact-form" onSubmit={onSubmit} noValidate>
      <label>
        Name
        <input name="name" autoComplete="name" maxLength={LIMITS.name} aria-invalid={!!errors.name} aria-describedby="err-name" />
        {errors.name && <span id="err-name" className="error">{errors.name}</span>}
      </label>
      <label>
        Email
        <input name="email" type="email" autoComplete="email" maxLength={LIMITS.email} aria-invalid={!!errors.email} aria-describedby="err-email" />
        {errors.email && <span id="err-email" className="error">{errors.email}</span>}
      </label>
      <label>
        Message
        <textarea name="message" rows={6} maxLength={LIMITS.messageMax} aria-invalid={!!errors.message} aria-describedby="err-message" />
        {errors.message && <span id="err-message" className="error">{errors.message}</span>}
      </label>
      {/* Honeypot: visually hidden and skipped by keyboard/screen readers. */}
      <div className="hp" aria-hidden="true">
        <label>
          Website
          <input name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>
      <button type="submit" disabled={status.kind === "sending"}>
        {status.kind === "sending" ? "Sending…" : "Send message"}
      </button>
      {status.kind === "error" && (
        <p role="alert" className="error">
          {status.message}
        </p>
      )}
    </form>
  );
}
