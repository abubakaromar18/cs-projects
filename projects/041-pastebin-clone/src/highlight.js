/**
 * Server-side syntax highlighting via highlight.js.
 *
 * Highlighting on the server means the page works with JavaScript disabled and
 * the browser only needs a stylesheet. highlight.js escapes the source text
 * itself, so its HTML output is safe to embed directly.
 */
import hljs from 'highlight.js';

/** A curated list for the language dropdown (any hljs language works via the API). */
export const POPULAR_LANGUAGES = [
  'auto', 'plaintext', 'bash', 'c', 'cpp', 'csharp', 'css', 'go', 'html', 'java',
  'javascript', 'json', 'kotlin', 'markdown', 'python', 'ruby', 'rust', 'sql',
  'swift', 'typescript', 'yaml',
];

/** Normalise a requested language; unknown names fall back to 'auto'. */
export function normalizeLanguage(lang) {
  if (!lang) return 'auto';
  const name = String(lang).trim().toLowerCase();
  if (name === 'auto' || name === 'plaintext' || name === 'text') {
    return name === 'text' ? 'plaintext' : name;
  }
  // 'html' is an alias of 'xml' in hljs; getLanguage resolves aliases.
  return hljs.getLanguage(name) ? name : 'auto';
}

/**
 * Highlight `code`.
 * @returns {{ html: string, language: string }} escaped HTML and the language used
 */
export function highlight(code, language = 'auto') {
  if (language === 'plaintext') {
    return { html: escapeHtml(code), language: 'plaintext' };
  }
  if (language !== 'auto' && hljs.getLanguage(language)) {
    const result = hljs.highlight(code, { language, ignoreIllegals: true });
    return { html: result.value, language };
  }
  // Auto-detection scores the text against every registered grammar and
  // picks the highest relevance; restrict it to popular languages for speed.
  const subset = POPULAR_LANGUAGES.filter((l) => l !== 'auto' && l !== 'plaintext');
  const result = hljs.highlightAuto(code, subset);
  return { html: result.value, language: result.language || 'plaintext' };
}

export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
