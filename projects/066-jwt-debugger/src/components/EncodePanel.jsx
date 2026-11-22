import { useState } from 'react';
import { HMAC_ALGS } from '../lib/algorithms.js';
import { sign } from '../lib/jwt.js';

const DEFAULT_PAYLOAD = JSON.stringify({ sub: 'user-42', role: 'reader' }, null, 2);

/** Build an HMAC-signed token from a JSON payload, optionally adding iat/exp. */
export default function EncodePanel({ onUseToken }) {
  const [alg, setAlg] = useState('HS256');
  const [payloadText, setPayloadText] = useState(DEFAULT_PAYLOAD);
  const [secret, setSecret] = useState('');
  const [ttl, setTtl] = useState(3600);
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');

  async function handleSign(e) {
    e.preventDefault();
    setError('');
    setOutput('');
    let payload;
    try {
      payload = JSON.parse(payloadText);
    } catch (err) {
      setError(`Payload is not valid JSON: ${err.message}`);
      return;
    }
    if (ttl > 0) {
      const now = Math.floor(Date.now() / 1000);
      payload = { iat: now, exp: now + Number(ttl), ...payload };
    }
    try {
      setOutput(await sign(payload, secret, { alg }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="panel" aria-label="Encode token" onSubmit={handleSign}>
      <h2 className="panel-title">Create a token</h2>
      <div className="row">
        <label className="field-label">
          Algorithm
          <select value={alg} onChange={(e) => setAlg(e.target.value)}>
            {HMAC_ALGS.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Lifetime (seconds, 0 = none)
          <input type="number" min="0" value={ttl} onChange={(e) => setTtl(e.target.value)} />
        </label>
      </div>
      <label className="field-label" htmlFor="payload-input">
        Payload JSON
      </label>
      <textarea id="payload-input" rows={6} value={payloadText} onChange={(e) => setPayloadText(e.target.value)} spellCheck={false} />
      <label className="field-label" htmlFor="secret-input">
        Secret
      </label>
      <input id="secret-input" type="text" value={secret} onChange={(e) => setSecret(e.target.value)} autoComplete="off" />
      <button type="submit">Sign</button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {output && (
        <>
          <pre className="token-output" aria-label="Signed token">
            {output}
          </pre>
          <button type="button" onClick={() => onUseToken(output, secret)}>
            Open in debugger
          </button>
        </>
      )}
    </form>
  );
}
