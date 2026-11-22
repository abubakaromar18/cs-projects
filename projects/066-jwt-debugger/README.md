# JWT Debugger

An offline JSON Web Token debugger built with React and the browser's WebCrypto API.
Paste a token to decode its header and payload, check `exp` / `nbf` / `iat` live,
get security warnings, and verify the signature with a shared secret or public key.
Nothing is sent over the network, so it is safe to use with tokens from your own systems.

## Features

- **Decode**: colour-coded header / payload / signature segments, pretty-printed JSON with
  hints for registered claims (`exp` shown as ISO time, etc.). Tolerates `Bearer ` prefixes
  and line breaks from copy-paste. Detects JWE (5-part) tokens and malformed segments.
- **Verify** with WebCrypto: `HS256/384/512`, `RS256/384/512`, `PS256/384/512`, `ES256/384/512`.
  HMAC secrets can be UTF-8 or base64url; public keys can be PEM (SPKI) or JWK JSON.
- **Claims**: live expiry countdown, configurable clock-skew leeway, millisecond-timestamp detection.
- **Security lint**: `alg: none`, missing `exp`, very long lifetimes, embedded `jwk`, remote
  `jku`/`x5u`, suspicious `kid` values, and secrets placed in the (unencrypted) payload.
- **Encode**: build an HMAC-signed token from JSON, then open it in the debugger.

## CS concepts demonstrated

- **Encoding vs. encryption**: base64url (RFC 4648 §5) is reversible formatting, not secrecy.
- **Message authentication codes and digital signatures**: HMAC-SHA2, RSA PKCS#1 v1.5,
  RSA-PSS and ECDSA, and why the signature covers the *original* `header.payload` bytes.
- **Algorithm-confusion attacks**: the verifier ties each `alg` to a key family and refuses a PEM
  public key as an HMAC secret, which blocks the classic RS256 → HS256 forgery (covered by a test).
- **Key formats**: PEM/DER (SPKI, PKCS#8) and JWK; stripping private members before verifying.
- **React patterns**: lifted state, `useMemo` for synchronous decoding, a custom hook for
  async verification that discards stale results, and an injectable clock for deterministic tests.

## Project layout

```
src/
  lib/base64url.js     base64url <-> bytes / UTF-8 (strict decoding)
  lib/algorithms.js    JWS alg -> WebCrypto parameters + key family
  lib/keys.js          PEM/JWK/secret -> CryptoKey, with misuse checks
  lib/jwt.js           decode / verify / sign
  lib/claims.js        time-claim checks, security lint (pure functions)
  hooks/               useNow (ticking clock), useVerification (async verify)
  components/          TokenInput, JsonView, ClaimsPanel, VerifyPanel, EncodePanel
  App.jsx              state and layout
test/                  Vitest unit tests + React Testing Library component tests
```

## Build, run, test

Requires Node 20+.

```bash
npm install
npm run dev      # http://localhost:5173
npm test         # 37 tests (library tests in Node, UI tests in jsdom)
npm run build    # static bundle in dist/
```

## Example

The app loads with a demo token signed with the fake secret `demo-secret-change-me`:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFkYSBMb3ZlbGFjZSIsImFkbWluIjp0cnVlLCJpYXQiOjE3NjcyMjU2MDAsImV4cCI6NDEwMjQ0NDgwMH0.N7g-bZySROlTlIk1T7mCKhqA-bP222ULdZBXz3qS0zM
```

The page shows the decoded payload with `"exp": 4102444800  // 2100-01-01T00:00:00.000Z`,
the badge **Time claims OK**, and **Signature verified**. Change one character of the secret
and the result becomes **Invalid signature: Signature does not match**.

The library also works on its own:

```js
import { sign, verify, decode } from './src/lib/jwt.js';

const token = await sign({ sub: 'user-42' }, 'secret', { alg: 'HS256' });
decode(token).payload;                                  // { sub: 'user-42' }
await verify(token, 'secret', { expectedAlg: 'HS256' }); // { valid: true, alg: 'HS256' }
```

Tests include the HS256 example from RFC 7515 Appendix A.1, round-trips for every
supported algorithm family, tampered payloads, `alg: none`, and an algorithm-confusion forgery.

## Possible extensions

- Fetch and cache a JWKS (with explicit user consent) and select the key by `kid`.
- Support JWE decryption (`RSA-OAEP`, `A256GCM`) and EdDSA (`Ed25519`) once widely available in WebCrypto.
- Add RSA/EC key-pair generation and asymmetric signing in the Encode tab.
- Ship a strict Content-Security-Policy (`connect-src 'none'`) in the production build.
- Side-by-side diff of two tokens' claims.
