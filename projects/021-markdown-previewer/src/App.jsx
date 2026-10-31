import { useCallback, useDeferredValue, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Editor } from './components/Editor.jsx';
import { Preview } from './components/Preview.jsx';
import { StatusBar } from './components/StatusBar.jsx';
import { Toolbar } from './components/Toolbar.jsx';
import { useLocalStorage } from './hooks/useLocalStorage.js';
import { insertLink, insertText, toggleLinePrefix, toggleWrap } from './lib/editing.js';
import { buildStandaloneHtml, downloadFile, readAsText, toFileName } from './lib/exportHtml.js';
import { documentStats, extractTitle, parseMarkdown, renderHtml } from './markdown/index.js';
import { SAMPLE_MARKDOWN } from './sample.js';

const STORAGE_KEY = 'markdown-previewer:source';
const VIEW_KEY = 'markdown-previewer:view';

export default function App({ initialSource = SAMPLE_MARKDOWN }) {
  const [source, setSource] = useLocalStorage(STORAGE_KEY, initialSource);
  const [view, setView] = useLocalStorage(VIEW_KEY, 'split', { debounceMs: 0 });
  const [message, setMessage] = useState('');

  const textareaRef = useRef(null);
  const previewRef = useRef(null);
  const pendingSelection = useRef(null);
  const scrollLock = useRef(null);
  const messageTimer = useRef(null);

  // Rendering is cheap but not free. useDeferredValue lets React keep the
  // textarea responsive and re-render the preview at lower priority.
  const deferredSource = useDeferredValue(source);
  const ast = useMemo(() => parseMarkdown(deferredSource), [deferredSource]);
  const html = useMemo(() => renderHtml(ast), [ast]);
  const stats = useMemo(() => documentStats(source), [source]);

  const flash = useCallback((text) => {
    setMessage(text);
    clearTimeout(messageTimer.current);
    messageTimer.current = setTimeout(() => setMessage(''), 2500);
  }, []);

  // After a programmatic edit, restore the selection once React has
  // committed the new value to the textarea.
  useLayoutEffect(() => {
    const sel = pendingSelection.current;
    const ta = textareaRef.current;
    if (sel && ta) {
      ta.setSelectionRange(sel.selectionStart, sel.selectionEnd);
      pendingSelection.current = null;
    }
  });

  /** Apply a pure edit function to the textarea's current value + selection. */
  const applyEdit = useCallback(
    (edit) => {
      const ta = textareaRef.current;
      if (!ta) return;
      const result = edit(ta.value, ta.selectionStart, ta.selectionEnd);
      if (!result) return;
      pendingSelection.current = result;
      setSource(result.value);
      ta.focus();
    },
    [setSource],
  );

  const handleFormat = useCallback(
    (action) => {
      const edits = {
        bold: (v, s, e) => toggleWrap(v, s, e, '**'),
        italic: (v, s, e) => toggleWrap(v, s, e, '*'),
        strike: (v, s, e) => toggleWrap(v, s, e, '~~'),
        code: (v, s, e) => toggleWrap(v, s, e, '`', '`', 'code'),
        heading: (v, s, e) => toggleLinePrefix(v, s, e, '## '),
        quote: (v, s, e) => toggleLinePrefix(v, s, e, '> '),
        list: (v, s, e) => toggleLinePrefix(v, s, e, '- '),
        link: insertLink,
      };
      if (edits[action]) applyEdit(edits[action]);
    },
    [applyEdit],
  );

  const handleIndent = useCallback(
    (outdent) => {
      applyEdit((v, s, e) => {
        const multiLine = v.slice(s, e).includes('\n');
        if (outdent) {
          const lineStart = v.lastIndexOf('\n', s - 1) + 1;
          return v.startsWith('  ', lineStart) || multiLine ? toggleLinePrefix(v, s, e, '  ') : null;
        }
        return multiLine ? toggleLinePrefix(v, s, e, '  ') : insertText(v, s, e, '  ');
      });
    },
    [applyEdit],
  );

  /**
   * Proportional scroll sync between panes. `scrollLock` records which pane
   * initiated the scroll so the echo event from the other pane is ignored.
   */
  const syncScroll = useCallback((from) => {
    const src = from === 'editor' ? textareaRef.current : previewRef.current;
    const dst = from === 'editor' ? previewRef.current : textareaRef.current;
    if (!src || !dst) return;
    if (scrollLock.current && scrollLock.current !== from) {
      scrollLock.current = null;
      return;
    }
    const max = src.scrollHeight - src.clientHeight;
    const ratio = max > 0 ? src.scrollTop / max : 0;
    scrollLock.current = from;
    dst.scrollTop = ratio * (dst.scrollHeight - dst.clientHeight);
  }, []);

  const title = extractTitle(ast);

  const handleExportHtml = () => {
    downloadFile(toFileName(title, 'html'), buildStandaloneHtml({ title, bodyHtml: html }), 'text/html');
    flash('Exported HTML');
  };

  const handleDownloadMarkdown = () => {
    downloadFile(toFileName(title, 'md'), source, 'text/markdown');
    flash('Saved Markdown file');
  };

  const handleCopyHtml = async () => {
    try {
      await navigator.clipboard.writeText(html);
      flash('HTML copied to clipboard');
    } catch {
      flash('Clipboard unavailable — use Export HTML instead');
    }
  };

  const handleOpenFile = async (file) => {
    try {
      setSource(await readAsText(file));
      flash(`Opened ${file.name}`);
    } catch {
      flash(`Could not read ${file.name}`);
    }
  };

  const handleReset = () => {
    if (source === SAMPLE_MARKDOWN || window.confirm('Replace your text with the sample document?')) {
      setSource(SAMPLE_MARKDOWN);
      flash('Reset to sample');
    }
  };

  return (
    <div className={`app view-${view}`}>
      <Toolbar
        view={view}
        onViewChange={setView}
        onFormat={handleFormat}
        onCopyHtml={handleCopyHtml}
        onExportHtml={handleExportHtml}
        onDownloadMarkdown={handleDownloadMarkdown}
        onOpenFile={handleOpenFile}
        onReset={handleReset}
      />
      <main className="workspace">
        {view !== 'preview' && (
          <Editor
            value={source}
            onChange={setSource}
            onFormat={handleFormat}
            onIndent={handleIndent}
            onScroll={() => syncScroll('editor')}
            textareaRef={textareaRef}
          />
        )}
        {view !== 'editor' && (
          <Preview
            html={html}
            stale={deferredSource !== source}
            onScroll={() => syncScroll('preview')}
            previewRef={previewRef}
          />
        )}
      </main>
      <StatusBar stats={stats} message={message} />
    </div>
  );
}
