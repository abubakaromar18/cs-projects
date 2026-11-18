/**
 * Lexer: turns a math expression string into a flat list of tokens.
 *
 * Token kinds:
 *   num    – numeric literal (supports decimals and exponents: 1.5e-3)
 *   ident  – identifier (variable, constant or function name)
 *   op     – one of + - * / ^
 *   lparen / rparen
 *   comma  – argument separator for multi-arg functions (max, min, ...)
 *   eof    – sentinel at the end of the stream
 *
 * Every token carries `pos` (index in the source) so the parser can produce
 * error messages that point at the offending character.
 */

export class SyntaxError extends Error {
  constructor(message, pos) {
    super(pos === undefined ? message : `${message} at position ${pos}`);
    this.name = 'SyntaxError';
    this.pos = pos;
  }
}

const isDigit = (c) => c >= '0' && c <= '9';
const isIdentStart = (c) => /[A-Za-z_]/.test(c);
const isIdentPart = (c) => /[A-Za-z0-9_]/.test(c);

export function tokenize(src) {
  const tokens = [];
  let i = 0;

  while (i < src.length) {
    const c = src[i];

    if (c === ' ' || c === '\t' || c === '\n') {
      i++;
      continue;
    }

    // Numbers: 12, 3.5, .5, 1e3, 2.5E-4
    if (isDigit(c) || (c === '.' && isDigit(src[i + 1] ?? ''))) {
      const start = i;
      while (isDigit(src[i] ?? '')) i++;
      if (src[i] === '.') {
        i++;
        while (isDigit(src[i] ?? '')) i++;
      }
      // Exponent only if followed by digits (so "2e" stays 2 * e).
      if ((src[i] === 'e' || src[i] === 'E')) {
        let j = i + 1;
        if (src[j] === '+' || src[j] === '-') j++;
        if (isDigit(src[j] ?? '')) {
          i = j;
          while (isDigit(src[i] ?? '')) i++;
        }
      }
      tokens.push({ type: 'num', value: Number(src.slice(start, i)), pos: start });
      continue;
    }

    if (isIdentStart(c)) {
      const start = i;
      while (i < src.length && isIdentPart(src[i])) i++;
      tokens.push({ type: 'ident', value: src.slice(start, i), pos: start });
      continue;
    }

    if ('+-*/^'.includes(c)) {
      tokens.push({ type: 'op', value: c, pos: i });
      i++;
      continue;
    }
    if (c === '(') { tokens.push({ type: 'lparen', pos: i++ }); continue; }
    if (c === ')') { tokens.push({ type: 'rparen', pos: i++ }); continue; }
    if (c === ',') { tokens.push({ type: 'comma', pos: i++ }); continue; }

    throw new SyntaxError(`Unexpected character '${c}'`, i);
  }

  tokens.push({ type: 'eof', pos: src.length });
  return tokens;
}
