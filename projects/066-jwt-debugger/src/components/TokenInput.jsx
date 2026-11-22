/**
 * Token textarea plus a colour-coded echo of the three segments, so it is
 * obvious which bytes are header, payload and signature.
 */
export default function TokenInput({ value, onChange, error }) {
  const parts = value.trim().split('.');
  return (
    <section className="panel">
      <label htmlFor="token" className="panel-title">
        Encoded token
      </label>
      <textarea
        id="token"
        className={`token-input ${error ? 'has-error' : ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        placeholder="Paste a JWT (header.payload.signature) — it never leaves this page"
        rows={6}
      />
      {value.trim() && parts.length === 3 && (
        <p className="segments" aria-label="Token segments">
          <span className="seg-header">{parts[0]}</span>.<span className="seg-payload">{parts[1]}</span>.
          <span className="seg-signature">{parts[2]}</span>
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}
