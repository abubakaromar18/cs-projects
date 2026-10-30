/**
 * Contact-form validation shared by the client component and the API route.
 * Running identical rules on both sides gives instant feedback in the browser
 * while the server remains the source of truth (never trust the client).
 */

export interface ContactInput {
  name: string;
  email: string;
  message: string;
  /** Honeypot: hidden from humans, bots tend to fill every field. */
  website?: string;
}

export type FieldErrors = Partial<Record<"name" | "email" | "message", string>>;

export type ValidationResult =
  | { ok: true; value: ContactInput; isSpam: boolean }
  | { ok: false; errors: FieldErrors };

export const LIMITS = { name: 100, email: 254, messageMin: 10, messageMax: 5000 } as const;

// Pragmatic email check: something@something.tld, no spaces. RFC 5322 is far
// more permissive, but this rejects typos without rejecting real addresses.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function asString(v: unknown): string {
  return typeof v === "string" ? v.trim() : "";
}

export function validateContact(input: unknown): ValidationResult {
  const obj = (input && typeof input === "object" ? input : {}) as Record<string, unknown>;
  const name = asString(obj.name);
  const email = asString(obj.email).toLowerCase();
  const message = asString(obj.message);
  const website = asString(obj.website);

  const errors: FieldErrors = {};
  if (!name) errors.name = "Please enter your name.";
  else if (name.length > LIMITS.name) errors.name = `Name must be at most ${LIMITS.name} characters.`;

  if (!email) errors.email = "Please enter your email.";
  else if (email.length > LIMITS.email || !EMAIL_RE.test(email)) errors.email = "Please enter a valid email address.";

  if (message.length < LIMITS.messageMin) errors.message = `Message must be at least ${LIMITS.messageMin} characters.`;
  else if (message.length > LIMITS.messageMax) errors.message = `Message must be at most ${LIMITS.messageMax} characters.`;

  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, value: { name, email, message }, isSpam: website !== "" };
}
