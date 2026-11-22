import { ALGORITHMS } from '../lib/algorithms.js';
import { useVerification } from '../hooks/useVerification.js';

const RESULT_TEXT = {
  idle: 'Enter a key to verify the signature',
  pending: 'Verifying…',
  valid: 'Signature verified',
  invalid: 'Invalid signature',
  error: 'Could not verify',
};

/** Key entry + signature verification result. The key family follows the header's alg. */
export default function VerifyPanel({ token, alg, keyMaterial, onKeyChange, secretIsBase64, onBase64Change }) {
  const family = ALGORITHMS[alg]?.family;
  const result = useVerification(token, keyMaterial, secretIsBase64, Boolean(family));

  if (!family) {
    return (
      <section className="panel" aria-label="Verify signature">
        <h2 className="panel-title">Verify signature</h2>
        <p role="status" className="verify-result verify-invalid">
          {String(alg).toLowerCase() === 'none'
            ? 'Unsigned token (alg "none") — there is nothing to verify'
            : `Unsupported algorithm "${alg}"`}
        </p>
      </section>
    );
  }

  const isHmac = family === 'hmac';
  return (
    <section className="panel" aria-label="Verify signature">
      <h2 className="panel-title">
        Verify signature <span className="badge">{alg}</span>
      </h2>
      <label htmlFor="key" className="field-label">
        {isHmac ? 'Shared secret' : 'Public key (PEM "PUBLIC KEY" or JWK JSON)'}
      </label>
      <textarea
        id="key"
        className="key-input"
        value={keyMaterial}
        onChange={(e) => onKeyChange(e.target.value)}
        rows={isHmac ? 2 : 7}
        spellCheck={false}
        placeholder={isHmac ? 'your-256-bit-secret' : '-----BEGIN PUBLIC KEY-----'}
      />
      {isHmac && (
        <label className="checkbox">
          <input type="checkbox" checked={secretIsBase64} onChange={(e) => onBase64Change(e.target.checked)} />
          Secret is base64url encoded
        </label>
      )}
      <p role="status" className={`verify-result verify-${result.state}`}>
        {RESULT_TEXT[result.state]}
        {result.reason ? `: ${result.reason}` : ''}
      </p>
    </section>
  );
}
