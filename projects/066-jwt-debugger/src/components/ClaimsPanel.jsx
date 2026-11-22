import { checkTimeClaims, lint } from '../lib/claims.js';

const STATUS_TEXT = {
  valid: 'Time claims OK',
  expired: 'Expired',
  'not-yet-valid': 'Not yet valid',
  invalid: 'Malformed time claims',
};

/** Live exp/nbf/iat checks and security lint warnings. */
export default function ClaimsPanel({ header, payload, now, leeway }) {
  const { status, checks } = checkTimeClaims(payload, now, leeway);
  const warnings = lint(header, payload);
  return (
    <section className="panel" aria-label="Claims">
      <h2 className="panel-title">
        Claims <span className={`badge badge-${status}`}>{STATUS_TEXT[status]}</span>
      </h2>
      {checks.length === 0 ? (
        <p className="muted">No exp / nbf / iat claims.</p>
      ) : (
        <ul className="checks">
          {checks.map((c) => (
            <li key={c.claim} className={c.ok ? 'ok' : 'bad'}>
              <code>{c.claim}</code> {c.message}
            </li>
          ))}
        </ul>
      )}
      {warnings.length > 0 && (
        <>
          <h3 className="subtitle">Security notes</h3>
          <ul className="warnings">
            {warnings.map((w) => (
              <li key={w.message} className={`sev-${w.severity}`}>
                <strong>{w.severity}</strong> {w.message}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
