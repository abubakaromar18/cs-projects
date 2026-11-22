import { describe, expect, it } from 'vitest';
import { checkTimeClaims, lint, relative } from '../src/lib/claims.js';

const NOW = 1_800_000_000;

describe('relative', () => {
  it('formats past and future deltas', () => {
    expect(relative(90)).toBe('in 1m');
    expect(relative(-7200)).toBe('2h ago');
    expect(relative(3 * 86400)).toBe('in 3d');
    expect(relative(0)).toBe('in 0s');
  });
});

describe('checkTimeClaims', () => {
  it('passes a currently-valid token', () => {
    const r = checkTimeClaims({ iat: NOW - 10, nbf: NOW - 10, exp: NOW + 10 }, NOW);
    expect(r.status).toBe('valid');
    expect(r.checks.every((c) => c.ok)).toBe(true);
  });

  it('flags expiry, honouring leeway', () => {
    expect(checkTimeClaims({ exp: NOW - 5 }, NOW).status).toBe('expired');
    expect(checkTimeClaims({ exp: NOW - 5 }, NOW, 30).status).toBe('valid');
    expect(checkTimeClaims({ exp: NOW }, NOW).status).toBe('expired'); // exp is exclusive
  });

  it('flags not-yet-valid tokens', () => {
    expect(checkTimeClaims({ nbf: NOW + 60 }, NOW).status).toBe('not-yet-valid');
    expect(checkTimeClaims({ nbf: NOW + 60 }, NOW, 60).status).toBe('valid');
  });

  it('flags iat in the future without changing status', () => {
    const r = checkTimeClaims({ iat: NOW + 600 }, NOW);
    expect(r.status).toBe('valid');
    expect(r.checks[0]).toMatchObject({ claim: 'iat', ok: false });
  });

  it('rejects non-numeric dates and hints at milliseconds', () => {
    expect(checkTimeClaims({ exp: '2030-01-01' }, NOW).status).toBe('invalid');
    const ms = checkTimeClaims({ exp: NOW * 1000 }, NOW);
    expect(ms.checks[0].message).toMatch(/milliseconds/);
  });
});

describe('lint', () => {
  const sev = (ws) => ws.map((w) => w.severity);

  it('is quiet for a well-formed token', () => {
    expect(lint({ alg: 'HS256' }, { exp: NOW + 60, iat: NOW })).toEqual([]);
  });

  it('warns about missing exp and long lifetimes', () => {
    expect(lint({ alg: 'HS256' }, {})[0].message).toMatch(/never expires/);
    expect(lint({ alg: 'HS256' }, { iat: NOW, exp: NOW + 365 * 86400 })[0].message).toMatch(/365 days/);
  });

  it('flags dangerous headers', () => {
    expect(sev(lint({ alg: 'none' }, { exp: 1 }))).toContain('high');
    expect(lint({ alg: 'RS256', jwk: {} }, { exp: 1 })[0].message).toMatch(/embeds/);
    expect(lint({ alg: 'RS256', jku: 'https://x' }, { exp: 1 })[0].message).toMatch(/jku/);
    expect(lint({ alg: 'HS256', kid: '../../dev/null' }, { exp: 1 })[0].message).toMatch(/kid/);
    expect(lint({ alg: 'HS256', kid: 'key-2026.v1' }, { exp: 1 })).toEqual([]);
  });

  it('flags secrets in the payload', () => {
    expect(lint({ alg: 'HS256' }, { exp: 1, password: 'x' })[0].message).toMatch(/password/);
  });
});
