/**
 * URL-safe random identifiers.
 *
 * Uses crypto-grade randomness with rejection sampling so every character of
 * the base62 alphabet is equally likely (a plain `byte % 62` would bias the
 * first 8 characters, because 256 is not a multiple of 62).
 */
import { randomBytes } from 'node:crypto';

export const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

// Largest multiple of 62 that fits in a byte: bytes >= this are rejected.
const LIMIT = 256 - (256 % ALPHABET.length); // 248

export function generateId(length = 8) {
  let id = '';
  while (id.length < length) {
    // Over-request a little so we rarely need a second round.
    for (const byte of randomBytes(length * 2)) {
      if (byte < LIMIT) {
        id += ALPHABET[byte % ALPHABET.length];
        if (id.length === length) break;
      }
    }
  }
  return id;
}

const ID_PATTERN = /^[A-Za-z0-9]{4,32}$/;

export function isValidId(id) {
  return typeof id === 'string' && ID_PATTERN.test(id);
}
