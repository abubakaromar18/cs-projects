/**
 * Pure text-editing operations used by the editor's toolbar and shortcuts.
 *
 * Each function takes the current value and selection and returns a new
 * { value, selectionStart, selectionEnd } instead of touching the DOM, which
 * keeps them trivially unit-testable.
 */

/**
 * Wrap the selection in `before`/`after` (e.g. `**` for bold). If the
 * selection is already wrapped, the markers are removed instead (toggle).
 * With an empty selection a placeholder is inserted and selected.
 */
export function toggleWrap(value, start, end, before, after = before, placeholder = 'text') {
  const outerStart = start - before.length;
  const outerEnd = end + after.length;
  if (
    outerStart >= 0 &&
    value.slice(outerStart, start) === before &&
    value.slice(end, outerEnd) === after
  ) {
    return {
      value: value.slice(0, outerStart) + value.slice(start, end) + value.slice(outerEnd),
      selectionStart: outerStart,
      selectionEnd: end - before.length,
    };
  }

  const selected = value.slice(start, end) || placeholder;
  return {
    value: value.slice(0, start) + before + selected + after + value.slice(end),
    selectionStart: start + before.length,
    selectionEnd: start + before.length + selected.length,
  };
}

/** Insert a Markdown link around the selection, selecting the URL slot. */
export function insertLink(value, start, end) {
  const label = value.slice(start, end) || 'link text';
  const url = 'https://';
  const inserted = `[${label}](${url})`;
  const urlStart = start + label.length + 3;
  return {
    value: value.slice(0, start) + inserted + value.slice(end),
    selectionStart: urlStart,
    selectionEnd: urlStart + url.length,
  };
}

/**
 * Add `prefix` to the start of every line touched by the selection (used
 * for headings, quotes and list items). Toggles off if all lines have it.
 */
export function toggleLinePrefix(value, start, end, prefix) {
  const lineStart = value.lastIndexOf('\n', start - 1) + 1;
  let lineEnd = value.indexOf('\n', end);
  if (lineEnd === -1) lineEnd = value.length;

  const lines = value.slice(lineStart, lineEnd).split('\n');
  const allPrefixed = lines.every((l) => l.startsWith(prefix));
  const changed = lines.map((l) => (allPrefixed ? l.slice(prefix.length) : prefix + l));
  const block = changed.join('\n');
  const delta = allPrefixed ? -prefix.length : prefix.length;

  return {
    value: value.slice(0, lineStart) + block + value.slice(lineEnd),
    selectionStart: Math.max(lineStart, start + delta),
    selectionEnd: lineStart + block.length - (lineEnd - end),
  };
}

/** Replace the selection with `text` and put the caret after it. */
export function insertText(value, start, end, text) {
  const caret = start + text.length;
  return { value: value.slice(0, start) + text + value.slice(end), selectionStart: caret, selectionEnd: caret };
}
