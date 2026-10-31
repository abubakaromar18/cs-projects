import { describe, expect, it } from 'vitest';
import { escapeHtml, markdownToHtml, sanitizeUrl } from '../src/markdown/index.js';

describe('escaping', () => {
  it('escapes raw HTML instead of passing it through', () => {
    const out = markdownToHtml('<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>');
    expect(out).not.toContain('<script');
    expect(out).not.toContain('<img');
    expect(out).toContain('&lt;script&gt;');
  });

  it('escapes quotes in attributes', () => {
    const out = markdownToHtml('[x](/a "\\" onmouseover=\\"alert(1)")');
    expect(out).toContain('title="&quot; onmouseover=&quot;alert(1)"');
  });

  it('escapes all five special characters', () => {
    expect(escapeHtml(`<a href="x" class='y'>&`)).toBe('&lt;a href=&quot;x&quot; class=&#39;y&#39;&gt;&amp;');
  });

  it('escapes heading ids and code languages', () => {
    expect(markdownToHtml('```"><script>\nx\n```')).not.toContain('"><script>');
  });
});

describe('sanitizeUrl', () => {
  it.each(['https://a.b', 'http://a.b', 'mailto:x@y.z', 'tel:+123', '/rel', '#frag', 'page.html'])('allows %s', (url) => {
    expect(sanitizeUrl(url)).not.toBeNull();
  });

  it.each([
    'javascript:alert(1)',
    'JaVaScRiPt:alert(1)',
    ' javascript:alert(1)',
    'java\tscript:alert(1)',
    'java\nscript:alert(1)',
    'vbscript:msgbox(1)',
    'data:text/html,<script>alert(1)</script>',
  ])('blocks %j', (url) => {
    expect(sanitizeUrl(url)).toBeNull();
  });

  it('allows only image data URLs, and only for images', () => {
    const png = 'data:image/png;base64,iVBORw0KGgo=';
    expect(sanitizeUrl(png)).toBeNull();
    expect(sanitizeUrl(png, { allowImageData: true })).toBe(png);
    expect(sanitizeUrl('data:image/svg+xml;base64,PHN2Zz4=', { allowImageData: true })).toBeNull();
  });

  it('drops the href of unsafe links but keeps their text', () => {
    expect(markdownToHtml('[click](javascript:alert(1))').trim()).toBe('<p>click</p>');
    expect(markdownToHtml('<javascript:alert(1)>').trim()).toBe('<p>javascript:alert(1)</p>');
    expect(markdownToHtml('![pic](javascript:x)').trim()).toBe('<p>pic</p>');
  });
});
