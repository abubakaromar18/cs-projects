import { describe, expect, it } from 'vitest';
import { markdownToHtml, parseInline, plainText } from '../src/markdown/index.js';

const inline = (md) => markdownToHtml(md).trim().replace(/^<p>|<\/p>$/g, '');

describe('emphasis', () => {
  it.each([
    ['*em*', '<em>em</em>'],
    ['_em_', '<em>em</em>'],
    ['**strong**', '<strong>strong</strong>'],
    ['__strong__', '<strong>strong</strong>'],
    ['***both***', '<em><strong>both</strong></em>'],
    ['~~gone~~', '<del>gone</del>'],
    ['*a **b** c*', '<em>a <strong>b</strong> c</em>'],
    ['**a *b* c**', '<strong>a <em>b</em> c</strong>'],
    ['**foo*', '*<em>foo</em>'],
    ['*foo**', '<em>foo</em>*'],
  ])('%s', (md, expected) => {
    expect(inline(md)).toBe(expected);
  });

  it('does not emphasise intraword underscores', () => {
    expect(inline('snake_case_name')).toBe('snake_case_name');
    expect(inline('in*tra*word')).toBe('in<em>tra</em>word');
  });

  it('requires flanking: no emphasis around whitespace', () => {
    expect(inline('a * b * c')).toBe('a * b * c');
    expect(inline('*not em *')).toBe('*not em *');
  });

  it('treats single tildes as text', () => {
    expect(inline('~a~')).toBe('~a~');
  });

  it('applies the rule of three', () => {
    expect(inline('*foo**bar**baz*')).toBe('<em>foo<strong>bar</strong>baz</em>');
  });
});

describe('code spans', () => {
  it('renders and escapes code', () => {
    expect(inline('`<b>`')).toBe('<code>&lt;b&gt;</code>');
  });

  it('uses backtick runs of equal length and strips one padding space', () => {
    expect(inline('`` a ` b ``')).toBe('<code>a ` b</code>');
  });

  it('leaves unmatched backticks literal', () => {
    expect(inline('a `b')).toBe('a `b');
  });

  it('takes precedence over emphasis', () => {
    expect(inline('*a `*` b*')).toBe('<em>a <code>*</code> b</em>');
  });
});

describe('links and images', () => {
  it('renders links with titles', () => {
    expect(inline('[x](https://a.b "T")')).toBe('<a href="https://a.b" title="T">x</a>');
  });

  it('parses formatting inside link text', () => {
    expect(inline('[**b**](/p)')).toBe('<a href="/p"><strong>b</strong></a>');
  });

  it('allows balanced parentheses and angle-bracket destinations', () => {
    expect(inline('[w](https://en.wikipedia.org/wiki/Foo_(bar))')).toBe(
      '<a href="https://en.wikipedia.org/wiki/Foo_(bar)">w</a>',
    );
    expect(inline('[s](<my file.md>)')).toBe('<a href="my%20file.md">s</a>');
  });

  it('allows nested brackets in link text', () => {
    expect(inline('[a [b] c](/x)')).toBe('<a href="/x">a [b] c</a>');
  });

  it('renders images with plain-text alt', () => {
    expect(inline('![a *b*](i.png "t")')).toBe('<img src="i.png" alt="a b" title="t" />');
  });

  it('renders autolinks and email autolinks', () => {
    expect(inline('<https://x.y/z>')).toBe('<a href="https://x.y/z">https://x.y/z</a>');
    expect(inline('<me@example.com>')).toBe('<a href="mailto:me@example.com">me@example.com</a>');
  });

  it('leaves malformed links as text', () => {
    expect(inline('[x](no-close')).toBe('[x](no-close');
    expect(inline('[x] (y)')).toBe('[x] (y)');
  });
});

describe('escapes and breaks', () => {
  it('backslash-escapes punctuation', () => {
    expect(inline('\\*not em\\*')).toBe('*not em*');
    expect(inline('\\[x](y)')).toBe('[x](y)');
  });

  it('keeps backslashes before non-punctuation', () => {
    expect(inline('C:\\path')).toBe('C:\\path');
  });

  it('creates hard breaks from two spaces or a backslash', () => {
    expect(inline('a  \nb')).toBe('a<br />\nb');
    expect(inline('a\\\nb')).toBe('a<br />\nb');
  });
});

describe('plainText', () => {
  it('flattens nested nodes', () => {
    expect(plainText(parseInline('**a** `b` [c](d)'))).toBe('a b c');
  });
});
