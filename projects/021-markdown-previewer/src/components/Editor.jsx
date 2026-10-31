/**
 * The Markdown source pane: a controlled <textarea> with keyboard shortcuts.
 * Text transformations live in lib/editing.js; this component only maps
 * keys to actions.
 */
export function Editor({ value, onChange, onFormat, onIndent, onScroll, textareaRef }) {
  function handleKeyDown(e) {
    const mod = e.ctrlKey || e.metaKey;
    if (e.key === 'Tab' && !mod && !e.altKey) {
      e.preventDefault();
      onIndent(e.shiftKey);
      return;
    }
    if (!mod) return;
    const shortcut = { b: 'bold', i: 'italic', k: 'link' }[e.key.toLowerCase()];
    if (shortcut) {
      e.preventDefault();
      onFormat(shortcut);
    }
  }

  return (
    <section className="pane editor-pane" aria-label="Markdown source">
      <div className="pane-title">Markdown</div>
      <textarea
        ref={textareaRef}
        className="editor"
        value={value}
        spellCheck="true"
        aria-label="Markdown editor"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onScroll={onScroll}
      />
    </section>
  );
}
