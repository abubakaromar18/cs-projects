import { describe, expect, it } from 'vitest';
import { decodeBytes, decodeText, encodeBytes, encodeText } from '../src/lib/base64url.js';

describe('base64url', () => {
  it('round-trips UTF-8 text including non-ASCII', () => {
    for (const s of ['', 'f', 'fo', 'foo', 'héllo wörld ✓', '{"a":1}']) {
      expect(decodeText(encodeText(s))).toBe(s);
    }
  });

  it('uses the URL-safe alphabet without padding', () => {
    const bytes = new Uint8Array([0xfb, 0xff, 0xbf]); // "+/+/" in standard base64
    expect(encodeBytes(bytes)).toBe('-_-_');
    expect(encodeText('a')).toBe('YQ');
  });

  it('accepts padded input', () => {
    expect(decodeText('YQ==')).toBe('a');
  });

  it('rejects characters from the standard alphabet and impossible lengths', () => {
    expect(() => decodeBytes('ab+/')).toThrow(/outside/);
    expect(() => decodeBytes('abcde')).toThrow(/length/);
  });

  it('rejects malformed UTF-8', () => {
    expect(() => decodeText(encodeBytes(new Uint8Array([0xff, 0xfe])))).toThrow();
  });
});
