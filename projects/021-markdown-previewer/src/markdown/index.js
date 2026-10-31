/**
 * Public API of the Markdown engine.
 *
 *   source text --parseMarkdown--> AST --renderHtml--> HTML string
 *
 * Keeping the AST as an explicit intermediate step lets the app reuse one
 * parse for several outputs (preview HTML, document title, outline).
 */
import { parseMarkdown } from './block.js';
import { plainText } from './inline.js';
import { renderHtml } from './render.js';

export { parseMarkdown } from './block.js';
export { parseInline, plainText } from './inline.js';
export { renderHtml, createSlugger } from './render.js';
export { escapeHtml, sanitizeUrl } from './escape.js';

export function markdownToHtml(source) {
  return renderHtml(parseMarkdown(source));
}

/** Text of the first level-1 heading, used as the exported document's title. */
export function extractTitle(ast, fallback = 'Untitled document') {
  for (const node of ast.children) {
    if (node.type === 'heading' && node.level === 1) {
      const text = plainText(node.children).trim();
      if (text) return text;
    }
  }
  return fallback;
}

/** Word / character counts and an estimated reading time (200 wpm). */
export function documentStats(source) {
  const words = String(source).match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu) ?? [];
  return {
    words: words.length,
    characters: String(source).length,
    readingMinutes: words.length === 0 ? 0 : Math.max(1, Math.round(words.length / 200)),
  };
}
