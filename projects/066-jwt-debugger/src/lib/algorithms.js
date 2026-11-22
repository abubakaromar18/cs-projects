/**
 * Mapping from JWS "alg" values (RFC 7518 §3.1) to WebCrypto parameters.
 *
 * Each entry says which key family the algorithm needs. The verifier uses
 * `family` to refuse mismatched keys, which is the classic defence against
 * "algorithm confusion" attacks (e.g. an attacker switching RS256 -> HS256 and
 * signing with the server's *public* key as an HMAC secret).
 */
export const ALGORITHMS = {
  HS256: { family: 'hmac', import: { name: 'HMAC', hash: 'SHA-256' }, sign: { name: 'HMAC' } },
  HS384: { family: 'hmac', import: { name: 'HMAC', hash: 'SHA-384' }, sign: { name: 'HMAC' } },
  HS512: { family: 'hmac', import: { name: 'HMAC', hash: 'SHA-512' }, sign: { name: 'HMAC' } },

  RS256: { family: 'rsa', import: { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, sign: { name: 'RSASSA-PKCS1-v1_5' } },
  RS384: { family: 'rsa', import: { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-384' }, sign: { name: 'RSASSA-PKCS1-v1_5' } },
  RS512: { family: 'rsa', import: { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-512' }, sign: { name: 'RSASSA-PKCS1-v1_5' } },

  // PSS salt length equals the hash output size, per RFC 7518 §3.5.
  PS256: { family: 'rsa', import: { name: 'RSA-PSS', hash: 'SHA-256' }, sign: { name: 'RSA-PSS', saltLength: 32 } },
  PS384: { family: 'rsa', import: { name: 'RSA-PSS', hash: 'SHA-384' }, sign: { name: 'RSA-PSS', saltLength: 48 } },
  PS512: { family: 'rsa', import: { name: 'RSA-PSS', hash: 'SHA-512' }, sign: { name: 'RSA-PSS', saltLength: 64 } },

  // JWS ECDSA signatures are raw R||S (IEEE P1363), which is exactly what
  // WebCrypto produces/consumes, so no DER conversion is needed.
  ES256: { family: 'ec', import: { name: 'ECDSA', namedCurve: 'P-256' }, sign: { name: 'ECDSA', hash: 'SHA-256' } },
  ES384: { family: 'ec', import: { name: 'ECDSA', namedCurve: 'P-384' }, sign: { name: 'ECDSA', hash: 'SHA-384' } },
  ES512: { family: 'ec', import: { name: 'ECDSA', namedCurve: 'P-521' }, sign: { name: 'ECDSA', hash: 'SHA-512' } },
};

export const SUPPORTED_ALGS = Object.keys(ALGORITHMS);
export const HMAC_ALGS = SUPPORTED_ALGS.filter((a) => ALGORITHMS[a].family === 'hmac');

export function getAlgorithm(alg) {
  if (typeof alg !== 'string') throw new Error('Header "alg" must be a string');
  if (alg.toLowerCase() === 'none') {
    throw new Error('alg "none" means the token is unsigned; refusing to treat it as verified');
  }
  const spec = ALGORITHMS[alg];
  if (!spec) throw new Error(`Unsupported algorithm "${alg}"`);
  return spec;
}
