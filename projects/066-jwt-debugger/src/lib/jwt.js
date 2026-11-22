/**
 * JWT (RFC 7519) compact-serialisation decode / verify / sign.
 *
 * A compact JWS is three base64url segments joined by dots:
 *     BASE64URL(header) . BASE64URL(payload) . BASE64URL(signature)
 * The signature covers the ASCII bytes of "header.payload" exactly as they
 * appear in the token, so we verify against the original segments rather
 * than re-encoding parsed JSON (which might reorder keys).
 */
import { getAlgorithm } from './algorithms.js';
import { decodeBytes, decodeText, encodeBytes, encodeText, utf8 } from './base64url.js';
import { importKey } from './keys.js';

export class JwtError extends Error {
  /** @param {string} message @param {'header'|'payload'|'signature'|'structure'} part */
  constructor(message, part) {
    super(message);
    this.name = 'JwtError';
    this.part = part;
  }
}

function parseJsonSegment(segment, part) {
  let text;
  try {
    text = decodeText(segment);
  } catch (err) {
    throw new JwtError(`${part} is not valid base64url/UTF-8: ${err.message}`, part);
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch (err) {
    throw new JwtError(`${part} is not valid JSON: ${err.message}`, part);
  }
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new JwtError(`${part} must be a JSON object`, part);
  }
  return value;
}

/**
 * Decode a token WITHOUT verifying it. Never trust the result for
 * authorisation decisions until `verify` succeeds.
 */
export function decode(token) {
  if (typeof token !== 'string') throw new JwtError('Token must be a string', 'structure');
  // Tolerate copy-paste artefacts: whitespace and a leading "Bearer ".
  const cleaned = token.trim().replace(/^Bearer\s+/i, '').replace(/\s+/g, '');
  const parts = cleaned.split('.');
  if (parts.length === 5) {
    throw new JwtError('This is a JWE (encrypted token, 5 parts); only signed JWS tokens can be decoded', 'structure');
  }
  if (parts.length !== 3) {
    throw new JwtError(`Expected 3 dot-separated parts, found ${parts.length}`, 'structure');
  }
  const [h, p, s] = parts;
  const header = parseJsonSegment(h, 'header');
  const payload = parseJsonSegment(p, 'payload');
  let signature;
  try {
    signature = decodeBytes(s);
  } catch (err) {
    throw new JwtError(`signature is not valid base64url: ${err.message}`, 'signature');
  }
  return {
    header,
    payload,
    signature,
    segments: { header: h, payload: p, signature: s },
    signingInput: `${h}.${p}`,
    token: cleaned,
  };
}

/**
 * Verify a token's signature with the given key material.
 *
 * @param {string} token
 * @param {string} keyMaterial - HMAC secret, PEM public key or JWK JSON
 * @param {{secretIsBase64?: boolean, expectedAlg?: string}} [opts]
 *   expectedAlg pins the algorithm instead of trusting the header — the
 *   recommended practice for real servers.
 * @returns {Promise<{valid: boolean, alg: string, reason?: string}>}
 */
export async function verify(token, keyMaterial, opts = {}) {
  const decoded = decode(token);
  const alg = decoded.header.alg;
  if (opts.expectedAlg && alg !== opts.expectedAlg) {
    return { valid: false, alg, reason: `Header alg "${alg}" does not match expected "${opts.expectedAlg}"` };
  }
  let spec;
  try {
    spec = getAlgorithm(alg);
  } catch (err) {
    return { valid: false, alg, reason: err.message };
  }
  const key = await importKey(alg, keyMaterial, { secretIsBase64: opts.secretIsBase64, usage: 'verify' });
  const ok = await crypto.subtle.verify(spec.sign, key, decoded.signature, utf8(decoded.signingInput));
  return ok ? { valid: true, alg } : { valid: false, alg, reason: 'Signature does not match' };
}

/**
 * Create a signed token. Used by the "Encode" tab and by tests.
 * @param {object} payload
 * @param {string} keyMaterial - HMAC secret, or PKCS#8 PEM / private JWK for asymmetric algs
 * @param {{alg?: string, header?: object, secretIsBase64?: boolean}} [opts]
 */
export async function sign(payload, keyMaterial, opts = {}) {
  const alg = opts.alg ?? 'HS256';
  const spec = getAlgorithm(alg);
  const header = { ...(opts.header ?? {}), alg, typ: opts.header?.typ ?? 'JWT' };
  const signingInput = `${encodeText(JSON.stringify(header))}.${encodeText(JSON.stringify(payload))}`;
  const key = await importKey(alg, keyMaterial, { secretIsBase64: opts.secretIsBase64, usage: 'sign' });
  const sig = await crypto.subtle.sign(spec.sign, key, utf8(signingInput));
  return `${signingInput}.${encodeBytes(new Uint8Array(sig))}`;
}
