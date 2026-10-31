const FORMAT_BUTTONS = [
  { action: 'bold', label: 'B', title: 'Bold (Ctrl/⌘+B)', className: 'fmt-bold' },
  { action: 'italic', label: 'I', title: 'Italic (Ctrl/⌘+I)', className: 'fmt-italic' },
  { action: 'strike', label: 'S', title: 'Strikethrough', className: 'fmt-strike' },
  { action: 'code', label: '</>', title: 'Inline code' },
  { action: 'heading', label: 'H', title: 'Heading' },
  { action: 'quote', label: '❝', title: 'Quote' },
  { action: 'list', label: '•', title: 'Bulleted list' },
  { action: 'link', label: '🔗', title: 'Link (Ctrl/⌘+K)' },
];

const VIEWS = [
  { id: 'editor', label: 'Editor' },
  { id: 'split', label: 'Split' },
  { id: 'preview', label: 'Preview' },
];

/**
 * Top bar: formatting buttons, view switcher and file actions.
 * It is purely presentational; every action is a callback from App.
 */
export function Toolbar({ view, onViewChange, onFormat, onCopyHtml, onExportHtml, onDownloadMarkdown, onOpenFile, onReset }) {
  return (
    <header className="toolbar" role="toolbar" aria-label="Editor toolbar">
      <h1 className="brand">Markdown Previewer</h1>

      <div className="group" aria-label="Formatting">
        {FORMAT_BUTTONS.map((b) => (
          <button
            key={b.action}
            type="button"
            className={`icon-btn ${b.className ?? ''}`}
            title={b.title}
            aria-label={b.title}
            // Keep focus (and the selection) in the textarea when clicking.
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onFormat(b.action)}
          >
            {b.label}
          </button>
        ))}
      </div>

      <div className="group segmented" role="radiogroup" aria-label="Layout">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            role="radio"
            aria-checked={view === v.id}
            className={view === v.id ? 'active' : ''}
            onClick={() => onViewChange(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div className="group actions">
        <label className="btn file-btn">
          Open .md
          <input
            type="file"
            accept=".md,.markdown,.txt,text/markdown,text/plain"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onOpenFile(file);
              e.target.value = ''; // allow re-opening the same file
            }}
          />
        </label>
        <button type="button" className="btn" onClick={onDownloadMarkdown}>
          Save .md
        </button>
        <button type="button" className="btn" onClick={onCopyHtml}>
          Copy HTML
        </button>
        <button type="button" className="btn primary" onClick={onExportHtml}>
          Export HTML
        </button>
        <button type="button" className="btn subtle" onClick={onReset}>
          Reset
        </button>
      </div>
    </header>
  );
}
