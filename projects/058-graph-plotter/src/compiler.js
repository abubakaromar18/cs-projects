/**
 * Compiles an AST into a plain JavaScript closure `(x) => number`.
 *
 * We deliberately do NOT use eval/new Function: the AST is walked once and
 * turned into a tree of nested closures. Each closure evaluates its children
 * and combines them, so the per-point cost is just a handful of function calls,
 * fast enough to sample thousands of points per frame.
 *
 * Name resolution happens at compile time, so unknown identifiers and wrong
 * argument counts are reported before any plotting starts.
 */

import { parse } from './parser.js';
import { SyntaxError } from './lexer.js';

export const CONSTANTS = {
  pi: Math.PI,
  e: Math.E,
  tau: 2 * Math.PI,
};

// name -> [arity, implementation]. arity -1 means variadic (>= 1 args).
export const FUNCTIONS = {
  sin: [1, Math.sin], cos: [1, Math.cos], tan: [1, Math.tan],
  asin: [1, Math.asin], acos: [1, Math.acos], atan: [1, Math.atan],
  sinh: [1, Math.sinh], cosh: [1, Math.cosh], tanh: [1, Math.tanh],
  sqrt: [1, Math.sqrt], cbrt: [1, Math.cbrt], abs: [1, Math.abs],
  exp: [1, Math.exp], ln: [1, Math.log], log: [1, Math.log10], log2: [1, Math.log2],
  floor: [1, Math.floor], ceil: [1, Math.ceil], round: [1, Math.round],
  sign: [1, Math.sign],
  sec: [1, (v) => 1 / Math.cos(v)], csc: [1, (v) => 1 / Math.sin(v)], cot: [1, (v) => 1 / Math.tan(v)],
  atan2: [2, Math.atan2],
  mod: [2, (a, b) => ((a % b) + b) % b], // mathematical modulo (always non-negative for b > 0)
  min: [-1, Math.min], max: [-1, Math.max],
};

const BINARY = {
  '+': (a, b) => a + b,
  '-': (a, b) => a - b,
  '*': (a, b) => a * b,
  '/': (a, b) => a / b,
  '^': (a, b) => Math.pow(a, b),
};

/**
 * Compile an AST node. `variable` is the name bound to the closure argument
 * (normally "x").
 */
export function compileAst(node, variable = 'x') {
  switch (node.type) {
    case 'num': {
      const v = node.value;
      return () => v;
    }
    case 'var': {
      if (node.name === variable) return (x) => x;
      if (node.name in CONSTANTS) {
        const v = CONSTANTS[node.name];
        return () => v;
      }
      throw new SyntaxError(`Unknown variable '${node.name}'`);
    }
    case 'unary': {
      const a = compileAst(node.arg, variable);
      return (x) => -a(x);
    }
    case 'binary': {
      const l = compileAst(node.left, variable);
      const r = compileAst(node.right, variable);
      const f = BINARY[node.op];
      return (x) => f(l(x), r(x));
    }
    case 'call': {
      const entry = FUNCTIONS[node.name];
      if (!entry) throw new SyntaxError(`Unknown function '${node.name}'`);
      const [arity, fn] = entry;
      const n = node.args.length;
      if (arity === -1 ? n < 1 : n !== arity) {
        const want = arity === -1 ? 'at least 1' : String(arity);
        throw new SyntaxError(`${node.name}() expects ${want} argument(s), got ${n}`);
      }
      const args = node.args.map((a) => compileAst(a, variable));
      if (args.length === 1) {
        const [a] = args;
        return (x) => fn(a(x));
      }
      return (x) => fn(...args.map((a) => a(x)));
    }
    default:
      throw new Error(`Unknown AST node type ${node.type}`);
  }
}

/** Convenience: parse + compile in one step. Throws SyntaxError on bad input. */
export function compile(src, variable = 'x') {
  return compileAst(parse(src), variable);
}

/**
 * Validate an expression without throwing. Returns { ok: true, fn } or
 * { ok: false, error } — useful for live-validating a text field.
 */
export function tryCompile(src, variable = 'x') {
  try {
    return { ok: true, fn: compile(src, variable) };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}
