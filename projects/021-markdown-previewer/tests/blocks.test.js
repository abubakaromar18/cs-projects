import { describe, expect, it } from 'vitest';
import { markdownToHtml, parseMarkdown } from '../src/markdown/index.js';

const html = (md) => markdownToHtml(md).trim();

describe('headings', () => {
  it('renders ATX headings with ids and strips closing hashes', () => {
    expect(html('# Hello')).toBe('<h1 id="hello">Hello</h1>');
    expect(html('### Deep ###')).toBe('<h3 id="deep">Deep</h3>');
  });

  it('requires a space after the hashes', () => {
    expect(html('#hashtag')).toBe('<p>#hashtag</p>');
  });

  it('supports setext headings', () => {
    expect(html('Title\n=====')).toBe('<h1 id="title">Title</h1>');
    expect(html('Sub\n---')).toBe('<h2 id="sub">Sub</h2>');
  });

  it('de-duplicates heading ids', () => {
    expect(html('# A\n# A')).toBe('<h1 id="a">A</h1>\n<h1 id="a-1">A</h1>');
  });
});

describe('paragraphs and rules', () => {
  it('separates paragraphs by blank lines and keeps soft breaks', () => {
    expect(html('one\ntwo\n\nthree')).toBe('<p>one\ntwo</p>\n<p>three</p>');
  });

  it('recognises thematic breaks', () => {
    expect(html('***')).toBe('<hr />');
    expect(html('- - -')).toBe('<hr />');
    expect(html('___')).toBe('<hr />');
  });

  it('lets a heading interrupt a paragraph', () => {
    expect(html('text\n# H')).toBe('<p>text</p>\n<h1 id="h">H</h1>');
  });
});

describe('code blocks', () => {
  it('renders fenced code with a language class and escapes content', () => {
    expect(html('```js\nif (a < b) {}\n```')).toBe('<pre><code class="language-js">if (a &lt; b) {}\n</code></pre>');
  });

  it('does not parse Markdown inside code', () => {
    expect(html('~~~\n**not bold**\n~~~')).toBe('<pre><code>**not bold**\n</code></pre>');
  });

  it('runs an unterminated fence to the end of the document', () => {
    expect(html('```\nopen')).toBe('<pre><code>open\n</code></pre>');
  });

  it('needs a closing fence at least as long as the opener', () => {
    expect(html('````\n```\n````')).toBe('<pre><code>```\n</code></pre>');
  });

  it('supports indented code blocks', () => {
    expect(html('    let x = 1;\n    x++;')).toBe('<pre><code>let x = 1;\nx++;\n</code></pre>');
  });
});

describe('block quotes', () => {
  it('nests recursively and supports lazy continuation', () => {
    expect(html('> a\nlazy\n> > b')).toBe('<blockquote>\n<p>a\nlazy</p>\n<blockquote>\n<p>b</p>\n</blockquote>\n</blockquote>');
  });

  it('may contain other blocks', () => {
    expect(html('> # Title\n> - item')).toBe(
      '<blockquote>\n<h1 id="title">Title</h1>\n<ul>\n<li>item</li>\n</ul>\n</blockquote>',
    );
  });
});

describe('lists', () => {
  it('renders tight bullet lists without <p>', () => {
    expect(html('- a\n- b')).toBe('<ul>\n<li>a</li>\n<li>b</li>\n</ul>');
  });

  it('renders loose lists with <p>', () => {
    expect(html('- a\n\n- b')).toBe('<ul>\n<li><p>a</p>\n</li>\n<li><p>b</p>\n</li>\n</ul>');
  });

  it('nests lists by indentation', () => {
    const ast = parseMarkdown('- a\n  - b\n    - c\n- d');
    const outer = ast.children[0];
    expect(outer.children).toHaveLength(2);
    const inner = outer.children[0].children[1];
    expect(inner.type).toBe('list');
    expect(inner.children[0].children[1].type).toBe('list');
  });

  it('keeps the start number of ordered lists', () => {
    expect(html('3. x\n4. y')).toBe('<ol start="3">\n<li>x</li>\n<li>y</li>\n</ol>');
    expect(html('1) x')).toBe('<ol>\n<li>x</li>\n</ol>');
  });

  it('starts a new list when the marker changes', () => {
    const ast = parseMarkdown('- a\n* b');
    expect(ast.children.map((n) => n.type)).toEqual(['list', 'list']);
  });

  it('allows multiple paragraphs and code in an item', () => {
    expect(html('1. first\n\n   more\n\n   ```\n   code\n   ```')).toBe(
      '<ol>\n<li><p>first</p>\n<p>more</p>\n<pre><code>code\n</code></pre>\n</li>\n</ol>',
    );
  });

  it('renders GFM task lists', () => {
    expect(html('- [ ] todo\n- [x] done')).toBe(
      '<ul class="contains-task-list">\n' +
        '<li class="task-list-item"><input type="checkbox" disabled /> todo</li>\n' +
        '<li class="task-list-item"><input type="checkbox" disabled checked /> done</li>\n</ul>',
    );
  });

  it('does not let "2." interrupt a paragraph', () => {
    expect(html('The year\n2. was fine')).toBe('<p>The year\n2. was fine</p>');
  });
});

describe('tables', () => {
  it('renders GFM tables with alignment', () => {
    expect(html('| a | b | c |\n|:--|:-:|--:|\n| 1 | 2 | 3 |')).toBe(
      '<table>\n<thead>\n<tr><th style="text-align: left">a</th><th style="text-align: center">b</th>' +
        '<th style="text-align: right">c</th></tr>\n</thead>\n<tbody>\n' +
        '<tr><td style="text-align: left">1</td><td style="text-align: center">2</td>' +
        '<td style="text-align: right">3</td></tr>\n</tbody>\n</table>',
    );
  });

  it('handles escaped pipes, pipes in code and ragged rows', () => {
    const out = html('a | b\n--|--\n\\| | `x|y`\nonly');
    expect(out).toContain('<td>|</td><td><code>x|y</code></td>');
    expect(out).toContain('<tr><td>only</td><td></td></tr>');
  });

  it('is not a table if column counts differ', () => {
    expect(html('a | b\n--')).toBe('<h2 id="a-b">a | b</h2>');
  });
});

describe('robustness', () => {
  it('normalises CRLF and tabs', () => {
    expect(html('- a\r\n\t- b')).toBe('<ul>\n<li>a\n<ul>\n<li>b</li>\n</ul>\n</li>\n</ul>');
  });

  it('returns nothing for empty input', () => {
    expect(html('')).toBe('');
    expect(html('\n\n   \n')).toBe('');
  });

  it('handles a large document quickly (linear-ish behaviour)', () => {
    const doc = '## Section\n\nSome *text* with `code` and [a link](https://x.y).\n\n- a\n- b\n\n'.repeat(2000);
    const t0 = performance.now();
    const out = markdownToHtml(doc);
    expect(performance.now() - t0).toBeLessThan(2000);
    expect(out.match(/<h2/g)).toHaveLength(2000);
  });
});
