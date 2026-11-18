import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tokenize } from '../src/lexer.js';
import { parse, toString } from '../src/parser.js';
import { compile, tryCompile } from '../src/compiler.js';

const show = (s) => toString(parse(s));
const near = (a, b, eps = 1e-12) => assert.ok(Math.abs(a - b) <= eps, `${a} !≈ ${b}`);

test('lexer handles decimals, exponents and identifiers', () => {
  const kinds = tokenize('1.5e-3 + .25*x2').map((t) => t.type);
  assert.deepEqual(kinds, ['num', 'op', 'num', 'op', 'ident', 'eof']);
  assert.equal(tokenize('1.5e-3')[0].value, 0.0015);
  // "2e" is 2 followed by the constant e, not a malformed exponent
  assert.deepEqual(tokenize('2e').map((t) => t.type), ['num', 'ident', 'eof']);
});

test('lexer rejects unknown characters with position', () => {
  assert.throws(() => tokenize('x $ 2'), /Unexpected character '\$' at position 2/);
});

test('operator precedence and associativity', () => {
  assert.equal(show('1 + 2 * 3'), '(1 + (2 * 3))');
  assert.equal(show('1 - 2 - 3'), '((1 - 2) - 3)');
  assert.equal(show('2 ^ 3 ^ 2'), '(2 ^ (3 ^ 2))');
  assert.equal(show('-x^2'), '(-(x ^ 2))');
  assert.equal(show('2^-x'), '(2 ^ (-x))');
});

test('implicit multiplication', () => {
  assert.equal(show('2x'), '(2 * x)');
  assert.equal(show('2x^2'), '(2 * (x ^ 2))');
  assert.equal(show('3(x+1)'), '(3 * (x + 1))');
  assert.equal(show('(x+1)(x-1)'), '((x + 1) * (x - 1))');
  assert.equal(show('2 sin(x)'), '(2 * sin(x))');
});

test('function calls with multiple arguments', () => {
  assert.equal(show('max(x, 1, 2)'), 'max(x, 1, 2)');
});

test('syntax errors are reported', () => {
  assert.throws(() => parse('1 +'), /Unexpected end/);
  assert.throws(() => parse('(1 + 2'), /Expected '\)'/);
  assert.throws(() => parse('1 + 2)'), /Unexpected '\)'/);
  assert.throws(() => parse(''), /Unexpected end/);
});

test('compiled functions evaluate correctly', () => {
  near(compile('x^2 + 2x + 1')(3), 16);
  near(compile('sin(pi/2)')(0), 1);
  near(compile('2^3^2')(0), 512);
  near(compile('-2^2')(0), -4);
  near(compile('ln(e)')(0), 1);
  near(compile('log(1000)')(0), 3);
  near(compile('mod(-1, 3)')(0), 2);
  near(compile('max(x, 4, 2)')(1), 4);
  near(compile('atan2(1, 1)')(0), Math.PI / 4);
  near(compile('tau')(0), 2 * Math.PI);
});

test('non-finite results are passed through (sampler handles them)', () => {
  assert.equal(compile('1/x')(0), Infinity);
  assert.ok(Number.isNaN(compile('sqrt(x)')(-1)));
});

test('compile-time name resolution errors', () => {
  assert.throws(() => compile('y + 1'), /Unknown variable 'y'/);
  assert.throws(() => compile('foo(x)'), /Unknown function 'foo'/);
  assert.throws(() => compile('sin(x, 2)'), /expects 1 argument/);
  assert.throws(() => compile('max()'), /expects at least 1/);
});

test('custom variable name', () => {
  near(compile('t^2', 't')(4), 16);
});

test('tryCompile never throws', () => {
  assert.equal(tryCompile('sin(').ok, false);
  assert.match(tryCompile('sin(').error, /Unexpected end/);
  assert.equal(tryCompile('cos(x)').ok, true);
});
