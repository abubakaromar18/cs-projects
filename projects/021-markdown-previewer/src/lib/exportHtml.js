/**
 * Export helpers: build a standalone HTML document from rendered Markdown
 * and hand files to the browser for download.
 */
import { escapeHtml } from '../markdown/index.js';

/** Minimal readable stylesheet embedded in exported documents. */
export const EXPORT_CSS = `
  :root { color-scheme: light dark; }
  body { max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6;
         font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  h1, h2 { border-bottom: 1px solid #8884; padding-bottom: .3em; }
  pre, code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  code { background: #8882; padding: .1em .3em; border-radius: 4px; }
  pre { background: #8882; padding: 1em; overflow-x: auto; border-radius: 6px; }
  pre code { background: none; padding: 0; }
  blockquote { margin: 0; padding: 0 1em; border-left: 4px solid #8886; color: #888; }
  table { border-collapse: collapse; }
  th, td { border: 1px solid #8886; padding: .4em .8em; }
  img { max-width: 100%; }
  .task-list-item { list-style: none; }
  .contains-task-list { padding-left: 1.2em; }
`;

export function buildStandaloneHtml({ title, bodyHtml }) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="generator" content="Markdown Previewer" />
<title>${escapeHtml(title)}</title>
<style>${EXPORT_CSS}</style>
</head>
<body>
${bodyHtml}</body>
</html>
`;
}

/** Turn a document title into a safe file name, e.g. "My Notes!" -> "my-notes". */
export function toFileName(title, extension) {
  const stem =
    title
      .toLowerCase()
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 60) || 'document';
  return `${stem}.${extension}`;
}

/** Trigger a browser download of `content` without any server round trip. */
export function downloadFile(fileName, content, mimeType) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke on the next tick so the download has started.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Read a File/Blob as UTF-8 text. FileReader is used rather than
 * Blob.prototype.text() because it is supported everywhere (including jsdom).
 */
export function readAsText(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}
