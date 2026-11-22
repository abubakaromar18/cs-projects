/**
 * Turning user-supplied key material into WebCrypto CryptoKey objects.
 *
 * Supported inputs:
 *   - HMAC: a UTF-8 secret, or a base64url-encoded secret (opt-in)
 *   - RSA / EC: a PEM "PUBLIC KEY" (SPKI) block, or a public JWK as JSON
 */
import { getAlgorithm } from './algorithms.js';
import { decodeBytes, utf8 } from './base64url.js';

/** Strip PEM armour and decode the base64 body into DER bytes. */
export function pemToDer(pem, expectedLabel = 'PUBLIC KEY') {
  const re = new RegExp(`-----BEGIN ${expectedLabel}-----([\\s\\S]*?)-----END ${expectedLabel}-----`);
  const match = pem.match(re);
  if (!match) {
    if (/BEGIN RSA PUBLIC KEY/.test(pem)) {
      throw new Error('PKCS#1 "RSA PUBLIC KEY" is not supported; convert to SPKI ("PUBLIC KEY")');
    }
    if (/PRIVATE KEY/.test(pem)) {
      throw new Error('That looks like a private key. Paste the public key to verify.');
    }
    throw new Error(`Expected a PEM block "-----BEGIN ${expectedLabel}-----"`);
  }
  const b64 = match[1].replace(/\s+/g, '');
  return decodeBytes(b64.replace(/\+/g, '-').replace(/\//g, '_'));
}

/** Convert DER bytes to a PEM string (used by tests and the "generate" helper). */
export function derToPem(der, label = 'PUBLIC KEY') {
  let binary = '';
  for (const b of new Uint8Array(der)) binary += String.fromCharCode(b);
  const lines = btoa(binary).match(/.{1,64}/g).join('\n');
  return `-----BEGIN ${label}-----\n${lines}\n-----END ${label}-----`;
}

/**
 * Import a key for `alg`.
 * @param {string} alg - JWS algorithm, e.g. "HS256"
 * @param {string} material - secret / PEM / JWK JSON
 * @param {{secretIsBase64?: boolean, usage?: 'verify'|'sign'}} [opts]
 */
export async function importKey(alg, material, opts = {}) {
  const spec = getAlgorithm(alg);
  const usage = opts.usage ?? 'verify';
  if (typeof material !== 'string' || material.length === 0) {
    throw new Error(spec.family === 'hmac' ? 'Enter the shared secret' : 'Enter a public key (PEM or JWK)');
  }

  if (spec.family === 'hmac') {
    if (/-----BEGIN/.test(material)) {
      // Refusing PEM here is what blocks RS256->HS256 confusion in the UI.
      throw new Error(`${alg} needs a shared secret, not a PEM key (possible algorithm-confusion attempt)`);
    }
    const raw = opts.secretIsBase64 ? decodeBytes(material.trim()) : utf8(material);
    return crypto.subtle.importKey('raw', raw, spec.import, false, [usage]);
  }

  const trimmed = material.trim();
  if (trimmed.startsWith('{')) {
    let jwk;
    try {
      jwk = JSON.parse(trimmed);
    } catch {
      throw new Error('Key looks like JSON but could not be parsed as a JWK');
    }
    const expectedKty = spec.family === 'rsa' ? 'RSA' : 'EC';
    if (jwk.kty !== expectedKty) throw new Error(`${alg} needs a JWK with kty "${expectedKty}", got "${jwk.kty}"`);
    if (usage === 'verify' && jwk.d) {
      // Strip private parts: a verifier should never need them.
      const { d, p, q, dp, dq, qi, ...pub } = jwk;
      jwk = pub;
    }
    // Drop "alg"/"key_ops" so WebCrypto doesn't reject on minor metadata mismatches.
    const { alg: _a, key_ops: _k, use: _u, ...clean } = jwk;
    return crypto.subtle.importKey('jwk', clean, spec.import, false, [usage]);
  }

  const format = usage === 'sign' ? 'pkcs8' : 'spki';
  const der = pemToDer(trimmed, usage === 'sign' ? 'PRIVATE KEY' : 'PUBLIC KEY');
  try {
    return await crypto.subtle.importKey(format, der, spec.import, false, [usage]);
  } catch (err) {
    throw new Error(`Key could not be imported for ${alg}: ${err.message}`);
  }
}
