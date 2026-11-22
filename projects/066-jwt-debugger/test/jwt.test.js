import { describe, expect, it } from 'vitest';
import { decode, sign, verify, JwtError } from '../src/lib/jwt.js';
import { derToPem } from '../src/lib/keys.js';
import { encodeText } from '../src/lib/base64url.js';
import { SAMPLE_SECRET, SAMPLE_TOKEN } from '../src/sample.js';

// RFC 7515 Appendix A.1 example (HS256) — an external test vector.
const RFC_TOKEN =
  'eyJ0eXAiOiJKV1QiLA0KICJhbGciOiJIUzI1NiJ9' +
  '.eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19yb290Ijp0cnVlfQ' +
  '.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk';
const RFC_KEY_B64 = 'AyM1SysPpbyDfgZld3umj1qzKObwVMkoqQ-EstJQLr_T-1qS0gZH75aKtMN3Yj0iPS4hcgUuTwjAzZr1Z9CAow';

async function rsaPair(name = 'RSASSA-PKCS1-v1_5') {
  const kp = await crypto.subtle.generateKey(
    { name, modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
    true,
    ['sign', 'verify'],
  );
  return {
    publicPem: derToPem(await crypto.subtle.exportKey('spki', kp.publicKey)),
    privatePem: derToPem(await crypto.subtle.exportKey('pkcs8', kp.privateKey), 'PRIVATE KEY'),
    publicJwk: await crypto.subtle.exportKey('jwk', kp.publicKey),
  };
}

describe('decode', () => {
  it('decodes header and payload of the sample token', () => {
    const d = decode(SAMPLE_TOKEN);
    expect(d.header).toEqual({ alg: 'HS256', typ: 'JWT' });
    expect(d.payload.name).toBe('Ada Lovelace');
    expect(d.signature).toBeInstanceOf(Uint8Array);
    expect(d.signature.length).toBe(32);
  });

  it('strips "Bearer " and whitespace', () => {
    const d = decode(`  Bearer ${SAMPLE_TOKEN.slice(0, 20)}\n${SAMPLE_TOKEN.slice(20)}  `);
    expect(d.token).toBe(SAMPLE_TOKEN);
  });

  it('reports structural problems with the failing part', () => {
    expect(() => decode('abc')).toThrow(/3 dot-separated/);
    expect(() => decode('a.b.c.d.e')).toThrow(/JWE/);
    try {
      decode(`${encodeText('not json')}.${encodeText('{}')}.`);
    } catch (err) {
      expect(err).toBeInstanceOf(JwtError);
      expect(err.part).toBe('header');
    }
    expect(() => decode(`${encodeText('{}')}.${encodeText('[1,2]')}.`)).toThrow(/payload must be a JSON object/);
  });
});

describe('HMAC verify / sign', () => {
  it('verifies the RFC 7515 A.1 test vector', async () => {
    expect(await verify(RFC_TOKEN, RFC_KEY_B64, { secretIsBase64: true })).toEqual({ valid: true, alg: 'HS256' });
  });

  it('verifies the bundled sample and rejects a wrong secret', async () => {
    expect((await verify(SAMPLE_TOKEN, SAMPLE_SECRET)).valid).toBe(true);
    const bad = await verify(SAMPLE_TOKEN, 'wrong');
    expect(bad.valid).toBe(false);
    expect(bad.reason).toMatch(/does not match/);
  });

  it.each(['HS256', 'HS384', 'HS512'])('round-trips %s', async (alg) => {
    const token = await sign({ sub: 'x' }, 's3cret', { alg });
    expect(decode(token).header).toEqual({ alg, typ: 'JWT' });
    expect((await verify(token, 's3cret')).valid).toBe(true);
  });

  it('detects a tampered payload', async () => {
    const token = await sign({ admin: false }, 'k');
    const [h, , s] = token.split('.');
    const forged = `${h}.${encodeText(JSON.stringify({ admin: true }))}.${s}`;
    expect((await verify(forged, 'k')).valid).toBe(false);
  });
});

describe('asymmetric algorithms', () => {
  it('signs and verifies RS256 with PEM and JWK public keys', async () => {
    const { publicPem, privatePem, publicJwk } = await rsaPair();
    const token = await sign({ sub: 'rsa' }, privatePem, { alg: 'RS256' });
    expect((await verify(token, publicPem)).valid).toBe(true);
    expect((await verify(token, JSON.stringify(publicJwk))).valid).toBe(true);
  });

  it('signs and verifies PS256', async () => {
    const { publicPem, privatePem } = await rsaPair('RSA-PSS');
    const token = await sign({ sub: 'pss' }, privatePem, { alg: 'PS256' });
    expect((await verify(token, publicPem)).valid).toBe(true);
  });

  it('signs and verifies ES256 (raw R||S signature)', async () => {
    const kp = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
    const priv = derToPem(await crypto.subtle.exportKey('pkcs8', kp.privateKey), 'PRIVATE KEY');
    const pub = derToPem(await crypto.subtle.exportKey('spki', kp.publicKey));
    const token = await sign({ sub: 'ec' }, priv, { alg: 'ES256' });
    expect(decode(token).signature.length).toBe(64);
    expect((await verify(token, pub)).valid).toBe(true);
  });

  it('rejects a private key pasted as the verification key', async () => {
    const { privatePem } = await rsaPair();
    const token = await sign({}, privatePem, { alg: 'RS256' });
    await expect(verify(token, privatePem)).rejects.toThrow(/private key/);
  });
});

describe('attack resistance', () => {
  it('refuses alg "none"', async () => {
    const unsigned = `${encodeText('{"alg":"none"}')}.${encodeText('{"admin":true}')}.`;
    const r = await verify(unsigned, 'anything');
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/unsigned/);
  });

  it('blocks RS256 -> HS256 algorithm confusion', async () => {
    const { publicPem } = await rsaPair();
    // Attacker signs an HS256 token using the server's public PEM as the HMAC secret.
    const header = encodeText('{"alg":"HS256","typ":"JWT"}');
    const payload = encodeText('{"admin":true}');
    const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(publicPem), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    const sig = new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${header}.${payload}`)));
    const { encodeBytes } = await import('../src/lib/base64url.js');
    const forged = `${header}.${payload}.${encodeBytes(sig)}`;
    await expect(verify(forged, publicPem)).rejects.toThrow(/algorithm-confusion/);
  });

  it('honours a pinned expectedAlg', async () => {
    const token = await sign({}, 'k', { alg: 'HS256' });
    const r = await verify(token, 'k', { expectedAlg: 'RS256' });
    expect(r).toMatchObject({ valid: false, reason: expect.stringMatching(/does not match expected/) });
  });

  it('rejects a JWK of the wrong key type', async () => {
    const token = await sign({}, (await rsaPair()).privatePem, { alg: 'RS256' });
    await expect(verify(token, '{"kty":"EC","crv":"P-256","x":"a","y":"b"}')).rejects.toThrow(/kty "RSA"/);
  });
});
