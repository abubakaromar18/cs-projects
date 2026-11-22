/**
 * Registered-claim inspection (RFC 7519 §4.1) and security lint checks.
 *
 * Everything here is pure: `now` is injected (seconds since epoch) so the
 * functions are deterministic and easy to test.
 */

export const CLAIM_DESCRIPTIONS = {
  iss: 'Issuer',
  sub: 'Subject',
  aud: 'Audience',
  exp: 'Expiration time',
  nbf: 'Not before',
  iat: 'Issued at',
  jti: 'JWT ID',
  alg: 'Signing algorithm',
  typ: 'Media type',
  kid: 'Key ID',
  cty: 'Content type',
};

const TIME_CLAIMS = ['exp', 'nbf', 'iat'];

/** Human-friendly relative duration, e.g. "in 5m" or "2h ago". */
export function relative(deltaSeconds) {
  const abs = Math.abs(deltaSeconds);
  const units = [
    ['d', 86400],
    ['h', 3600],
    ['m', 60],
    ['s', 1],
  ];
  let text = '0s';
  for (const [label, size] of units) {
    if (abs >= size) {
      text = `${Math.floor(abs / size)}${label}`;
      break;
    }
  }
  return deltaSeconds >= 0 ? `in ${text}` : `${text} ago`;
}

/**
 * Validate time-based claims.
 * @returns {{status: 'valid'|'expired'|'not-yet-valid'|'invalid', checks: Array}}
 */
export function checkTimeClaims(payload, now, leewaySeconds = 0) {
  const checks = [];
  let status = 'valid';

  for (const name of TIME_CLAIMS) {
    if (!(name in payload)) continue;
    const value = payload[name];
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      checks.push({ claim: name, ok: false, message: `${name} must be a NumericDate (seconds), got ${JSON.stringify(value)}` });
      status = 'invalid';
      continue;
    }
    // A value > 1e11 is almost certainly milliseconds — a very common bug.
    const msHint = value > 1e11 ? ' (looks like milliseconds, should be seconds)' : '';
    const when = `${new Date(value * 1000).toISOString()} (${relative(value - now)})`;

    if (name === 'exp') {
      const ok = now < value + leewaySeconds;
      if (!ok && status === 'valid') status = 'expired';
      checks.push({ claim: 'exp', ok, message: `${ok ? 'Expires' : 'Expired'} ${when}${msHint}` });
    } else if (name === 'nbf') {
      const ok = now + leewaySeconds >= value;
      if (!ok && status === 'valid') status = 'not-yet-valid';
      checks.push({ claim: 'nbf', ok, message: `${ok ? 'Valid since' : 'Not valid until'} ${when}${msHint}` });
    } else {
      const ok = value <= now + leewaySeconds;
      checks.push({ claim: 'iat', ok, message: `${ok ? 'Issued' : 'Issued in the future:'} ${when}${msHint}` });
    }
  }
  return { status, checks };
}

/**
 * Lint a decoded token for common security smells. Returns warnings, each
 * with a severity of 'high' | 'medium' | 'low'.
 */
export function lint(header, payload) {
  const warnings = [];
  const alg = header.alg;
  if (typeof alg === 'string' && alg.toLowerCase() === 'none') {
    warnings.push({ severity: 'high', message: 'alg "none": token is unsigned and must never be accepted' });
  }
  if (!('exp' in payload)) {
    warnings.push({ severity: 'medium', message: 'No "exp" claim: token never expires' });
  } else if (typeof payload.exp === 'number' && typeof payload.iat === 'number') {
    const lifetime = payload.exp - payload.iat;
    if (lifetime > 30 * 86400) {
      warnings.push({ severity: 'low', message: `Long lifetime (${Math.round(lifetime / 86400)} days)` });
    }
  }
  if ('jku' in header || 'x5u' in header) {
    warnings.push({ severity: 'medium', message: 'Header references a remote key URL (jku/x5u); servers must allow-list these' });
  }
  if ('jwk' in header) {
    warnings.push({ severity: 'high', message: 'Header embeds its own "jwk"; never trust a key supplied by the token itself' });
  }
  if (typeof header.kid === 'string' && /\.\.|[/\\'"]/.test(header.kid)) {
    warnings.push({ severity: 'medium', message: '"kid" contains path/quote characters; watch for injection in key lookup' });
  }
  const sensitive = Object.keys(payload).filter((k) => /pass(word)?|secret|ssn|card/i.test(k));
  if (sensitive.length) {
    warnings.push({ severity: 'high', message: `Payload may contain secrets (${sensitive.join(', ')}); JWT payloads are only encoded, not encrypted` });
  }
  return warnings;
}
