import { useMemo, useState } from 'react';
import TokenInput from './components/TokenInput.jsx';
import JsonView from './components/JsonView.jsx';
import ClaimsPanel from './components/ClaimsPanel.jsx';
import VerifyPanel from './components/VerifyPanel.jsx';
import EncodePanel from './components/EncodePanel.jsx';
import { useNow } from './hooks/useNow.js';
import { decode } from './lib/jwt.js';
import { SAMPLE_SECRET, SAMPLE_TOKEN } from './sample.js';

/**
 * Root component. All state lives here; decoding is synchronous and memoised,
 * verification is async inside VerifyPanel. Nothing is sent over the network.
 */
export default function App({ initialToken = SAMPLE_TOKEN, initialKey = SAMPLE_SECRET, now: fixedNow }) {
  const [tab, setTab] = useState('decode');
  const [token, setToken] = useState(initialToken);
  const [keyMaterial, setKeyMaterial] = useState(initialKey);
  const [secretIsBase64, setSecretIsBase64] = useState(false);
  const [leeway, setLeeway] = useState(0);
  const liveNow = useNow();
  const now = fixedNow ?? liveNow;

  const { decoded, error } = useMemo(() => {
    if (!token.trim()) return { decoded: null, error: '' };
    try {
      return { decoded: decode(token), error: '' };
    } catch (err) {
      return { decoded: null, error: err.message };
    }
  }, [token]);

  function openToken(newToken, secret) {
    setToken(newToken);
    setKeyMaterial(secret);
    setSecretIsBase64(false);
    setTab('decode');
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>JWT Debugger</h1>
        <p className="muted">Decode, inspect and verify JSON Web Tokens entirely in your browser.</p>
        <nav className="tabs" role="tablist">
          {['decode', 'encode'].map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
              {t === 'decode' ? 'Decode & verify' : 'Encode'}
            </button>
          ))}
        </nav>
      </header>

      {tab === 'encode' ? (
        <EncodePanel onUseToken={openToken} />
      ) : (
        <main className="grid">
          <div className="col">
            <TokenInput value={token} onChange={setToken} error={error} />
            {decoded && (
              <VerifyPanel
                token={decoded.token}
                alg={decoded.header.alg}
                keyMaterial={keyMaterial}
                onKeyChange={setKeyMaterial}
                secretIsBase64={secretIsBase64}
                onBase64Change={setSecretIsBase64}
              />
            )}
          </div>
          <div className="col">
            {decoded && (
              <>
                <JsonView title="Header" data={decoded.header} className="border-header" />
                <JsonView title="Payload" data={decoded.payload} className="border-payload" />
                <label className="field-label leeway">
                  Clock-skew leeway (s)
                  <input type="number" min="0" value={leeway} onChange={(e) => setLeeway(Number(e.target.value) || 0)} />
                </label>
                <ClaimsPanel header={decoded.header} payload={decoded.payload} now={now} leeway={leeway} />
              </>
            )}
          </div>
        </main>
      )}
    </div>
  );
}
