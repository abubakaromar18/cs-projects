/**
 * Recursive-descent parser producing an abstract syntax tree (AST).
 *
 * Grammar (lowest to highest precedence):
 *
 *   expr     := term (('+' | '-') term)*
 *   term     := unary (('*' | '/') unary | implicit)*
 *   unary    := ('-' | '+') unary | power
 *   power    := postfix ('^' unary)?          // right-associative: 2^3^2 = 2^9
 *   postfix  := primary
 *   primary  := num | ident | ident '(' args ')' | '(' expr ')'
 *
 * Note that `-x^2` parses as `-(x^2)` (as in standard math notation) because
 * unary minus sits *below* exponentiation, while `2^-x` still works because the
 * exponent is itself a `unary`.
 *
 * Implicit multiplication is supported where it is unambiguous for a
 * plotting tool: `2x`, `3(x+1)`, `(x+1)(x-1)`, `2 sin(x)`, `x pi`.
 *
 * AST node shapes:
 *   { type: 'num', value }
 *   { type: 'var', name }
 *   { type: 'unary', op, arg }
 *   { type: 'binary', op, left, right }
 *   { type: 'call', name, args }
 */

import { tokenize, SyntaxError } from './lexer.js';

export function parse(src) {
  const tokens = tokenize(src);
  let p = 0;

  const peek = () => tokens[p];
  const next = () => tokens[p++];
  const isOp = (t, ops) => t.type === 'op' && ops.includes(t.value);

  function expect(type) {
    const t = next();
    if (t.type !== type) {
      throw new SyntaxError(`Expected ${type === 'rparen' ? "')'" : type}`, t.pos);
    }
    return t;
  }

  // Can this token begin a factor? Used to detect implicit multiplication.
  const startsFactor = (t) => t.type === 'num' || t.type === 'ident' || t.type === 'lparen';

  function parseExpr() {
    let left = parseTerm();
    while (isOp(peek(), '+-')) {
      const op = next().value;
      left = { type: 'binary', op, left, right: parseTerm() };
    }
    return left;
  }

  function parseTerm() {
    let left = parseUnary();
    for (;;) {
      const t = peek();
      if (isOp(t, '*/')) {
        next();
        left = { type: 'binary', op: t.value, left, right: parseUnary() };
      } else if (startsFactor(t)) {
        // Implicit multiplication binds like '*': "2x^2" = 2 * (x^2).
        left = { type: 'binary', op: '*', left, right: parsePower() };
      } else {
        return left;
      }
    }
  }

  function parseUnary() {
    const t = peek();
    if (isOp(t, '+-')) {
      next();
      const arg = parseUnary();
      return t.value === '-' ? { type: 'unary', op: '-', arg } : arg;
    }
    return parsePower();
  }

  function parsePower() {
    const base = parsePrimary();
    if (isOp(peek(), '^')) {
      next();
      return { type: 'binary', op: '^', left: base, right: parseUnary() };
    }
    return base;
  }

  function parsePrimary() {
    const t = next();
    switch (t.type) {
      case 'num':
        return { type: 'num', value: t.value };
      case 'ident': {
        if (peek().type === 'lparen') {
          next();
          const args = [];
          if (peek().type !== 'rparen') {
            args.push(parseExpr());
            while (peek().type === 'comma') {
              next();
              args.push(parseExpr());
            }
          }
          expect('rparen');
          return { type: 'call', name: t.value, args };
        }
        return { type: 'var', name: t.value };
      }
      case 'lparen': {
        const e = parseExpr();
        expect('rparen');
        return e;
      }
      case 'eof':
        throw new SyntaxError('Unexpected end of expression', t.pos);
      default:
        throw new SyntaxError(`Unexpected '${t.value ?? t.type}'`, t.pos);
    }
  }

  const ast = parseExpr();
  const end = peek();
  if (end.type !== 'eof') {
    throw new SyntaxError(`Unexpected '${end.value ?? (end.type === 'rparen' ? ')' : end.type)}'`, end.pos);
  }
  return ast;
}

/** Pretty-print an AST back into a fully-parenthesised string (handy for tests). */
export function toString(node) {
  switch (node.type) {
    case 'num': return String(node.value);
    case 'var': return node.name;
    case 'unary': return `(-${toString(node.arg)})`;
    case 'binary': return `(${toString(node.left)} ${node.op} ${toString(node.right)})`;
    case 'call': return `${node.name}(${node.args.map(toString).join(', ')})`;
    default: throw new Error(`Unknown node ${node.type}`);
  }
}
