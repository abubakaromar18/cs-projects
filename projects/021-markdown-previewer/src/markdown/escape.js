/**
 * Output-safety helpers.
 *
 * The previewer injects rendered HTML into the page, so every byte of user
 * text must be escaped and every URL must be checked. Raw HTML in the
 * Markdown source is never passed through: it is escaped like any other text.
 */

const HTML_ESCAPES = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/** Escape text for use in HTML element content or a quoted attribute. */
export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
}

const SAFE_SCHEMES = new Set(['http', 'https', 'mailto', 'tel']);
const SAFE_IMAGE_DATA = /^data:image\/(?:png|gif|jpe?g|webp);/i;

/**
 * Return a URL that is safe to place in href/src, or null if it uses a
 * dangerous scheme such as `javascript:`.
 *
 * Browsers ignore control characters and whitespace inside a scheme
 * ("java\tscript:" still runs), so those are stripped before the check.
 */
export function sanitizeUrl(url, { allowImageData = false } = {}) {
  const trimmed = String(url).trim();
  const probe = trimmed.replace(/[\u0000- \u007F]+/g, '');
  const match = /^([a-z][a-z0-9+.-]*):/i.exec(probe);
  if (!match) return trimmed.replace(/ /g, '%20'); // relative URL or #fragment
  const scheme = match[1].toLowerCase();
  if (SAFE_SCHEMES.has(scheme)) return trimmed.replace(/ /g, '%20');
  if (scheme === 'data' && allowImageData && SAFE_IMAGE_DATA.test(probe)) return probe;
  return null;
}
