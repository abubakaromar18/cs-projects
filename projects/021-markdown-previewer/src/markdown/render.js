/**
 * HTML renderer: a recursive tree walk over the AST produced by the parser.
 *
 * All text goes through escapeHtml() and all URLs through sanitizeUrl(), so
 * the output is safe to inject with dangerouslySetInnerHTML.
 */
import { escapeHtml, sanitizeUrl } from './escape.js';
import { plainText } from './inline.js';

/** Turn heading text into a URL fragment, de-duplicating repeats. */
export function createSlugger() {
  const seen = new Map();
  return (text) => {
    const base =
      text
        .toLowerCase()
        .trim()
        .replace(/[^\p{L}\p{N}\s-]/gu, '')
        .replace(/\s+/g, '-') || 'section';
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    return count === 0 ? base : `${base}-${count}`;
  };
}

export function renderHtml(ast) {
  const slug = createSlugger();
  return renderBlocks(ast.children, { slug, tight: false });
}

function renderBlocks(blocks, ctx) {
  return blocks.map((b) => renderBlock(b, ctx)).join('');
}

function renderBlock(node, ctx) {
  switch (node.type) {
    case 'heading': {
      const id = ctx.slug(plainText(node.children));
      return `<h${node.level} id="${escapeHtml(id)}">${renderInline(node.children)}</h${node.level}>\n`;
    }
    case 'paragraph':
      // Tight list items render their paragraphs without <p> wrappers.
      return ctx.tight ? renderInline(node.children) : `<p>${renderInline(node.children)}</p>\n`;
    case 'hr':
      return '<hr />\n';
    case 'code': {
      const cls = node.lang ? ` class="language-${escapeHtml(node.lang)}"` : '';
      const body = node.value ? `${escapeHtml(node.value)}\n` : '';
      return `<pre><code${cls}>${body}</code></pre>\n`;
    }
    case 'blockquote':
      return `<blockquote>\n${renderBlocks(node.children, { ...ctx, tight: false })}</blockquote>\n`;
    case 'list': {
      const tag = node.ordered ? 'ol' : 'ul';
      const start = node.ordered && node.start !== 1 ? ` start="${node.start}"` : '';
      const isTaskList = node.children.some((item) => item.checked !== null);
      const cls = isTaskList ? ' class="contains-task-list"' : '';
      const items = node.children.map((item) => renderListItem(item, { ...ctx, tight: !node.loose })).join('');
      return `<${tag}${start}${cls}>\n${items}</${tag}>\n`;
    }
    case 'table':
      return renderTable(node);
    default:
      return '';
  }
}

function renderListItem(item, ctx) {
  let checkbox = '';
  let cls = '';
  if (item.checked !== null) {
    cls = ' class="task-list-item"';
    checkbox = `<input type="checkbox" disabled${item.checked ? ' checked' : ''} /> `;
  }
  let body = renderBlocks(item.children, ctx);
  // In tight lists a nested block (e.g. a sub-list) starts on its own line.
  if (ctx.tight && item.children.length > 1) {
    body = item.children
      .map((child) => (child.type === 'paragraph' ? renderInline(child.children) : `\n${renderBlock(child, ctx)}`))
      .join('');
  }
  return `<li${cls}>${checkbox}${body}</li>\n`;
}

function renderTable(node) {
  const alignAttr = (c) => (node.align[c] ? ` style="text-align: ${node.align[c]}"` : '');
  const head = node.head.map((cell, c) => `<th${alignAttr(c)}>${renderInline(cell)}</th>`).join('');
  const rows = node.rows
    .map((row) => `<tr>${row.map((cell, c) => `<td${alignAttr(c)}>${renderInline(cell)}</td>`).join('')}</tr>\n`)
    .join('');
  const body = rows ? `<tbody>\n${rows}</tbody>\n` : '';
  return `<table>\n<thead>\n<tr>${head}</tr>\n</thead>\n${body}</table>\n`;
}

export function renderInline(nodes) {
  let out = '';
  for (const n of nodes) {
    switch (n.type) {
      case 'text':
        out += escapeHtml(n.value);
        break;
      case 'code':
        out += `<code>${escapeHtml(n.value)}</code>`;
        break;
      case 'break':
        out += '<br />\n';
        break;
      case 'em':
      case 'strong':
      case 'del':
        out += `<${n.type}>${renderInline(n.children)}</${n.type}>`;
        break;
      case 'link': {
        const href = sanitizeUrl(n.href);
        const title = n.title ? ` title="${escapeHtml(n.title)}"` : '';
        // An unsafe link keeps its text but loses the href entirely.
        out += href === null ? renderInline(n.children) : `<a href="${escapeHtml(href)}"${title}>${renderInline(n.children)}</a>`;
        break;
      }
      case 'image': {
        const src = sanitizeUrl(n.src, { allowImageData: true });
        const title = n.title ? ` title="${escapeHtml(n.title)}"` : '';
        out += src === null ? escapeHtml(n.alt) : `<img src="${escapeHtml(src)}" alt="${escapeHtml(n.alt)}"${title} />`;
        break;
      }
      default:
        break;
    }
  }
  return out;
}
