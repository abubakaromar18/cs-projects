/**
 * Block parser: splits a document into lines and builds a tree of block
 * nodes (headings, paragraphs, lists, quotes, code, tables, rules).
 *
 * It is a recursive-descent parser over lines. Container blocks (block
 * quotes and list items) strip their own prefix from each of their lines and
 * then call parseBlocks() again on the result, so nesting to any depth falls
 * out of the recursion.
 *
 * The text of leaf blocks is handed to the inline parser as the tree is built.
 */
import { parseInline } from './inline.js';

const RE = {
  blank: /^[ \t]*$/,
  fence: /^( {0,3})(`{3,}|~{3,})[ \t]*(.*)$/,
  atx: /^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$/,
  setext: /^ {0,3}(=+|-+)[ \t]*$/,
  hr: /^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/,
  quote: /^ {0,3}> ?(.*)$/,
  listItem: /^( {0,3})([-*+]|\d{1,9}[.)])( +|$)(.*)$/,
  indentedCode: /^ {4}/,
  tableDelim: /^ *\|? *:?-+:? *(?:\| *:?-+:? *)*\|? *$/,
  task: /^\[([ xX])\][ \t]+/,
};

/** Parse a full Markdown string into a `document` node. */
export function parseMarkdown(source) {
  const lines = String(source)
    .replace(/\r\n?/g, '\n')
    .split('\n')
    // Expand leading tabs so indentation arithmetic only deals with spaces.
    .map((line) => line.replace(/^[ \t]+/, (ws) => ws.replace(/\t/g, '    ')));
  return { type: 'document', children: parseBlocks(lines) };
}

export function parseBlocks(lines) {
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (RE.blank.test(line)) {
      i++;
      continue;
    }

    const parsed =
      parseFence(lines, i) ??
      parseIndentedCode(lines, i) ??
      parseAtxHeading(lines, i) ??
      parseRule(lines, i) ??
      parseQuote(lines, i) ??
      parseList(lines, i) ??
      parseTable(lines, i) ??
      parseParagraph(lines, i);

    blocks.push(parsed.node);
    i = parsed.next;
  }
  return blocks;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const leadingSpaces = (line) => /^ */.exec(line)[0].length;

function matchFence(line) {
  const m = RE.fence.exec(line);
  if (!m) return null;
  // A backtick fence's info string may not itself contain backticks.
  if (m[2][0] === '`' && m[3].includes('`')) return null;
  return { indent: m[1].length, char: m[2][0], length: m[2].length, info: m[3].trim() };
}

function matchListItem(line) {
  const m = RE.listItem.exec(line);
  if (!m) return null;
  const [, indentStr, marker, spaces, rest] = m;
  const indent = indentStr.length;
  const ordered = /\d/.test(marker[0]);
  // More than 4 spaces after the marker means the content is indented code;
  // in that case only one space belongs to the marker.
  const gap = spaces.length === 0 || spaces.length > 4 ? 1 : spaces.length;
  const content = spaces.length > 4 ? ' '.repeat(spaces.length - 1) + rest : rest;
  return {
    indent,
    ordered,
    number: ordered ? parseInt(marker, 10) : null,
    delimiter: ordered ? marker.at(-1) : marker,
    contentOffset: indent + marker.length + gap,
    content,
  };
}

/** Lines that may interrupt a paragraph without a blank line before them. */
function interruptsParagraph(line) {
  if (RE.atx.test(line) || RE.hr.test(line) || RE.quote.test(line) || matchFence(line)) return true;
  const item = matchListItem(line);
  // Per CommonMark, only non-empty items, and ordered lists starting at 1, interrupt.
  return Boolean(item && item.content.trim() !== '' && (!item.ordered || item.number === 1));
}

function splitTableRow(line) {
  let row = line.trim();
  if (row.startsWith('|')) row = row.slice(1);
  if (row.endsWith('|') && !row.endsWith('\\|')) row = row.slice(0, -1);
  const cells = [];
  let cell = '';
  let inCode = false;
  for (let k = 0; k < row.length; k++) {
    const c = row[k];
    if (c === '\\' && row[k + 1] === '|') {
      cell += '|';
      k++;
    } else if (c === '`') {
      inCode = !inCode;
      cell += c;
    } else if (c === '|' && !inCode) {
      cells.push(cell.trim());
      cell = '';
    } else {
      cell += c;
    }
  }
  cells.push(cell.trim());
  return cells;
}

// ---------------------------------------------------------------------------
// Block constructs. Each returns { node, next } or null if it does not apply.
// ---------------------------------------------------------------------------

function parseFence(lines, start) {
  const open = matchFence(lines[start]);
  if (!open) return null;
  const body = [];
  let i = start + 1;
  for (; i < lines.length; i++) {
    const close = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(lines[i]);
    if (close && close[1][0] === open.char && close[1].length >= open.length) {
      i++;
      break;
    }
    // Remove up to the opening fence's indentation from each content line.
    body.push(lines[i].slice(Math.min(open.indent, leadingSpaces(lines[i]))));
  }
  const lang = open.info.split(/\s+/)[0] || null;
  return { node: { type: 'code', lang, value: body.join('\n') }, next: i };
}

function parseIndentedCode(lines, start) {
  if (!RE.indentedCode.test(lines[start])) return null;
  const body = [];
  let i = start;
  while (i < lines.length && (RE.indentedCode.test(lines[i]) || RE.blank.test(lines[i]))) {
    body.push(lines[i].slice(4));
    i++;
  }
  while (body.length && RE.blank.test(body.at(-1))) body.pop();
  return { node: { type: 'code', lang: null, value: body.join('\n') }, next: i };
}

function parseAtxHeading(lines, start) {
  const m = RE.atx.exec(lines[start]);
  if (!m) return null;
  return {
    node: { type: 'heading', level: m[1].length, children: parseInline(m[2] ?? '') },
    next: start + 1,
  };
}

function parseRule(lines, start) {
  return RE.hr.test(lines[start]) ? { node: { type: 'hr' }, next: start + 1 } : null;
}

function parseQuote(lines, start) {
  if (!RE.quote.test(lines[start])) return null;
  const inner = [];
  let i = start;
  while (i < lines.length) {
    const m = RE.quote.exec(lines[i]);
    if (m) {
      inner.push(m[1]);
    } else if (
      // "Lazy" continuation: an unmarked line continues a quoted paragraph.
      !RE.blank.test(lines[i]) &&
      !RE.blank.test(inner.at(-1) ?? '') &&
      !interruptsParagraph(lines[i])
    ) {
      inner.push(lines[i]);
    } else {
      break;
    }
    i++;
  }
  return { node: { type: 'blockquote', children: parseBlocks(inner) }, next: i };
}

function parseList(lines, start) {
  const first = matchListItem(lines[start]);
  if (!first || RE.hr.test(lines[start])) return null;

  const items = [];
  let current = null;
  let sawBlank = false;
  let loose = false;
  let inFence = false;
  let i = start;

  while (i < lines.length) {
    const line = lines[i];

    if (RE.blank.test(line)) {
      if (current) current.lines.push('');
      sawBlank = true;
      i++;
      continue;
    }

    // Indented at least to the item's content column: belongs to the item.
    if (current && leadingSpaces(line) >= current.contentOffset) {
      const stripped = line.slice(current.contentOffset);
      // A blank line between two direct children makes the list loose.
      if (sawBlank && !inFence && !/^ /.test(stripped)) loose = true;
      if (matchFence(stripped)) inFence = !inFence;
      current.lines.push(stripped);
      sawBlank = false;
      i++;
      continue;
    }

    const m = matchListItem(line);
    if (m && !RE.hr.test(line) && m.ordered === first.ordered && m.delimiter === first.delimiter) {
      if (sawBlank && current) loose = true;
      current = { lines: [m.content], contentOffset: m.contentOffset };
      items.push(current);
      sawBlank = false;
      inFence = Boolean(matchFence(m.content));
      i++;
      continue;
    }

    // Lazy continuation of the item's paragraph.
    if (current && !sawBlank && !inFence && !interruptsParagraph(line) && current.lines.at(-1).trim() !== '') {
      current.lines.push(line.trim());
      i++;
      continue;
    }
    break;
  }

  const children = items.map((item) => {
    let itemLines = item.lines;
    while (itemLines.length && RE.blank.test(itemLines.at(-1))) itemLines = itemLines.slice(0, -1);

    // GFM task list item: "- [ ] todo" / "- [x] done"
    let checked = null;
    const task = RE.task.exec(itemLines[0] ?? '');
    if (task) {
      checked = task[1] !== ' ';
      itemLines = [itemLines[0].slice(task[0].length), ...itemLines.slice(1)];
    }
    return { type: 'listItem', checked, children: parseBlocks(itemLines) };
  });

  return {
    node: { type: 'list', ordered: first.ordered, start: first.number, loose, children },
    next: i,
  };
}

function parseTable(lines, start) {
  const header = lines[start];
  const delim = lines[start + 1];
  if (!header.includes('|') || delim === undefined || !RE.tableDelim.test(delim)) return null;

  const headerCells = splitTableRow(header);
  const delimCells = splitTableRow(delim);
  if (headerCells.length !== delimCells.length) return null;

  const align = delimCells.map((cell) => {
    const left = cell.startsWith(':');
    const right = cell.endsWith(':');
    return left && right ? 'center' : right ? 'right' : left ? 'left' : null;
  });

  const rows = [];
  let i = start + 2;
  while (i < lines.length && !RE.blank.test(lines[i]) && !interruptsParagraph(lines[i])) {
    const cells = splitTableRow(lines[i]);
    // Rows are normalised to the header's width: extra cells are dropped,
    // missing cells are empty.
    rows.push(headerCells.map((_, c) => parseInline(cells[c] ?? '')));
    i++;
  }

  return {
    node: { type: 'table', align, head: headerCells.map((c) => parseInline(c)), rows },
    next: i,
  };
}

function parseParagraph(lines, start) {
  const text = [lines[start].replace(/^ +/, '')];
  let i = start + 1;
  while (i < lines.length) {
    const line = lines[i];
    const setext = RE.setext.exec(line);
    if (setext) {
      return {
        node: {
          type: 'heading',
          level: setext[1][0] === '=' ? 1 : 2,
          children: parseInline(text.join('\n')),
        },
        next: i + 1,
      };
    }
    if (RE.blank.test(line) || interruptsParagraph(line)) break;
    text.push(line.replace(/^ +/, ''));
    i++;
  }
  // Keep trailing spaces on inner lines (hard breaks) but not at the very end.
  const value = text.join('\n').replace(/[ \t]+$/, '');
  return { node: { type: 'paragraph', children: parseInline(value) }, next: i };
}
