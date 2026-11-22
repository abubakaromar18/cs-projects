import { CLAIM_DESCRIPTIONS } from '../lib/claims.js';

/** Format NumericDate claims as ISO strings next to their raw value. */
function annotate(key, value) {
  if (['exp', 'nbf', 'iat'].includes(key) && typeof value === 'number') {
    return new Date(value * 1000).toISOString();
  }
  return CLAIM_DESCRIPTIONS[key] ?? null;
}

/** Pretty-printed JSON object with per-key hints for registered claims. */
export default function JsonView({ title, data, className }) {
  return (
    <section className={`panel ${className ?? ''}`} aria-label={title}>
      <h2 className="panel-title">{title}</h2>
      <pre className="json">
        {'{\n'}
        {Object.entries(data).map(([k, v], i, arr) => {
          const note = annotate(k, v);
          return (
            <span key={k} className="json-line">
              {'  '}
              <span className="json-key">"{k}"</span>: <span className="json-value">{JSON.stringify(v)}</span>
              {i < arr.length - 1 ? ',' : ''}
              {note && <span className="json-note">{`  // ${note}`}</span>}
              {'\n'}
            </span>
          );
        })}
        {'}'}
      </pre>
    </section>
  );
}
