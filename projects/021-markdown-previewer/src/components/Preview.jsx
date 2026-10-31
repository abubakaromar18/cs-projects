/**
 * Rendered output pane.
 *
 * dangerouslySetInnerHTML is acceptable here only because our own renderer
 * produced the HTML: it escapes all text, drops raw HTML and rejects unsafe
 * URL schemes (see markdown/escape.js and the security tests).
 */
export function Preview({ html, stale, onScroll, previewRef }) {
  return (
    <section className="pane preview-pane" aria-label="Rendered preview">
      <div className="pane-title">
        Preview {stale && <span className="stale" aria-hidden="true">updating…</span>}
      </div>
      <article
        ref={previewRef}
        className="preview markdown-body"
        data-testid="preview"
        onScroll={onScroll}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </section>
  );
}
