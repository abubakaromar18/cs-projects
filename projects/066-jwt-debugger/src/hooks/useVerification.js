import { useEffect, useState } from 'react';
import { verify } from '../lib/jwt.js';

/**
 * Run signature verification asynchronously whenever the inputs change.
 * Stale results are discarded so a slow RSA import can't overwrite a newer answer.
 */
export function useVerification(token, keyMaterial, secretIsBase64, enabled) {
  const [result, setResult] = useState({ state: 'idle' });

  useEffect(() => {
    if (!enabled || !keyMaterial) {
      setResult({ state: 'idle' });
      return undefined;
    }
    let cancelled = false;
    setResult({ state: 'pending' });
    verify(token, keyMaterial, { secretIsBase64 })
      .then((r) => !cancelled && setResult(r.valid ? { state: 'valid', alg: r.alg } : { state: 'invalid', reason: r.reason }))
      .catch((err) => !cancelled && setResult({ state: 'error', reason: err.message }));
    return () => {
      cancelled = true;
    };
  }, [token, keyMaterial, secretIsBase64, enabled]);

  return result;
}
