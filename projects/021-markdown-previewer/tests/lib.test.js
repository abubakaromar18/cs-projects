import { describe, expect, it } from 'vitest';
import { insertLink, insertText, toggleLinePrefix, toggleWrap } from '../src/lib/editing.js';
import { buildStandaloneHtml, toFileName } from '../src/lib/exportHtml.js';
import { documentStats, extractTitle, parseMarkdown } from '../src/markdown/index.js';

describe('toggleWrap', () => {
  it('wraps the selection and keeps it selected', () => {
    const r = toggleWrap('say hi now', 4, 6, '**');
    expect(r.value).toBe('say **hi** now');
    expect(r.value.slice(r.selectionStart, r.selectionEnd)).toBe('hi');
  });

  it('unwraps an already-wrapped selection', () => {
    const r = toggleWrap('say **hi** now', 6, 8, '**');
    expect(r).toEqual({ value: 'say hi now', selectionStart: 4, selectionEnd: 6 });
  });

  it('inserts a selected placeholder for an empty selection', () => {
    const r = toggleWrap('', 0, 0, '*');
    expect(r.value).toBe('*text*');
    expect(r.value.slice(r.selectionStart, r.selectionEnd)).toBe('text');
  });
});

describe('insertLink', () => {
  it('uses the selection as label and selects the URL', () => {
    const r = insertLink('see docs', 4, 8);
    expect(r.value).toBe('see [docs](https://)');
    expect(r.value.slice(r.selectionStart, r.selectionEnd)).toBe('https://');
  });
});

describe('toggleLinePrefix', () => {
  it('prefixes every selected line, then removes it again', () => {
    const v = 'a\nb\nc';
    const on = toggleLinePrefix(v, 0, 3, '- ');
    expect(on.value).toBe('- a\n- b\nc');
    const off = toggleLinePrefix(on.value, on.selectionStart, on.selectionEnd, '- ');
    expect(off.value).toBe(v);
  });

  it('works on the line containing the caret', () => {
    expect(toggleLinePrefix('x\ntitle', 4, 4, '## ').value).toBe('x\n## title');
  });
});

describe('insertText', () => {
  it('replaces the selection and moves the caret', () => {
    expect(insertText('abcd', 1, 3, '--')).toEqual({ value: 'a--d', selectionStart: 3, selectionEnd: 3 });
  });
});

describe('export', () => {
  it('builds a complete, escaped standalone document', () => {
    const doc = buildStandaloneHtml({ title: 'A <b> & C', bodyHtml: '<p>hi</p>\n' });
    expect(doc.startsWith('<!doctype html>')).toBe(true);
    expect(doc).toContain('<title>A &lt;b&gt; &amp; C</title>');
    expect(doc).toContain('<body>\n<p>hi</p>\n</body>');
    expect(doc).toContain('<style>');
  });

  it('derives safe file names', () => {
    expect(toFileName('My Notes: Week #3!', 'html')).toBe('my-notes-week-3.html');
    expect(toFileName('Café résumé', 'md')).toBe('cafe-resume.md');
    expect(toFileName('???', 'md')).toBe('document.md');
  });

  it('takes the title from the first h1', () => {
    expect(extractTitle(parseMarkdown('## sub\n# **Main** title'))).toBe('Main title');
    expect(extractTitle(parseMarkdown('no heading'))).toBe('Untitled document');
  });
});

describe('documentStats', () => {
  it('counts words, characters and reading time', () => {
    expect(documentStats('')).toEqual({ words: 0, characters: 0, readingMinutes: 0 });
    expect(documentStats("# Hi there, it's me")).toEqual({ words: 4, characters: 19, readingMinutes: 1 });
    expect(documentStats('word '.repeat(1000)).readingMinutes).toBe(5);
  });
});
