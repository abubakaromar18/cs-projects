/**
 * Base64url (RFC 4648 §5) helpers.
 *
 * JWTs use the URL-safe alphabet ("-" and "_" instead of "+" and "/") and
 * drop the "=" padding. These helpers work on Uint8Array so they handle
 * arbitrary binary (signatures) as well as UTF-8 text (header / payload).
 * They rely only on atob/btoa + TextEncoder, available in browsers and Node 18+.
 */

const VALID = /^[A-Za-z0-9_-]*$/;

/** Encode bytes as unpadded base64url. */
export function encodeBytes(bytes) {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** Decode unpadded (or padded) base64url to bytes. Throws on bad input. */
export function decodeBytes(input) {
  const s = input.replace(/=+$/, '');
  if (!VALID.test(s)) {
    throw new Error('Invalid base64url: contains characters outside [A-Za-z0-9_-]');
  }
  // A base64 group of 4 chars encodes 3 bytes; a remainder of 1 char is impossible.
  if (s.length % 4 === 1) throw new Error('Invalid base64url: bad length');
  const b64 = s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (s.length % 4)) % 4);
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}

const encoder = new TextEncoder();
// fatal: true makes malformed UTF-8 throw instead of silently producing U+FFFD.
const decoder = new TextDecoder('utf-8', { fatal: true });

export const encodeText = (text) => encodeBytes(encoder.encode(text));
export const decodeText = (input) => decoder.decode(decodeBytes(input));
export const utf8 = (text) => encoder.encode(text);
