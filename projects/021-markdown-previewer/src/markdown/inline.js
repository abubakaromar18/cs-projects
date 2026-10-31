/**
 * Inline parser: turns the text of one block (a paragraph, heading, table
 * cell...) into a list of inline nodes.
 *
 * It works in two passes, following the CommonMark design:
 *   1. A left-to-right scanner recognises self-contained constructs (code
 *      spans, links, images, autolinks, escapes, line breaks) and records
 *      runs of `*`, `_` and `~` as *delimiter* nodes, noting whether each run
 *      can open and/or close emphasis ("flanking" rules).
 *   2. processEmphasis() walks the delimiters, pairing each closer with the
 *      nearest compatible opener behind it, and wraps everything between them
 *      in an em / strong / del node. Unpaired delimiters become plain text.
 *
 * Node shapes:
 *   { type: 'text', value }      { type: 'code', value }      { type: 'break' }
 *   { type: 'em' | 'strong' | 'del', children }
 *   { type: 'link', href, title, children }
 *   { type: 'image', src, alt, title }
 */

const ESCAPABLE = /[!-/:-@[-`{-~]/; // ASCII punctuation
const isWhitespace = (c) => /\s/.test(c);
const isPunct = (c) => /[\p{P}\p{S}]/u.test(c);

export function parseInline(src) {
  const nodes = [];
  let text = '';
  let i = 0;

  const flush = () => {
    if (text) nodes.push({ type: 'text', value: text });
    text = '';
  };

  while (i < src.length) {
    const ch = src[i];

    if (ch === '\\') {
      const next = src[i + 1];
      if (next === '\n') {
        flush();
        nodes.push({ type: 'break' });
        i += 2;
        continue;
      }
      if (next !== undefined && ESCAPABLE.test(next)) {
        text += next;
        i += 2;
        continue;
      }
      text += ch;
      i++;
      continue;
    }

    if (ch === '`') {
      const span = parseCodeSpan(src, i);
      if (span) {
        flush();
        nodes.push(span.node);
        i = span.end;
      } else {
        // No matching closer: the whole backtick run is literal.
        const run = runLength(src, i, '`');
        text += src.slice(i, i + run);
        i += run;
      }
      continue;
    }

    if (ch === '!' && src[i + 1] === '[') {
      const link = parseLinkLike(src, i + 1);
      if (link) {
        flush();
        nodes.push({
          type: 'image',
          src: link.dest,
          title: link.title,
          alt: plainText(parseInline(link.label)),
        });
        i = link.end;
        continue;
      }
    }

    if (ch === '[') {
      const link = parseLinkLike(src, i);
      if (link) {
        flush();
        nodes.push({
          type: 'link',
          href: link.dest,
          title: link.title,
          children: parseInline(link.label),
        });
        i = link.end;
        continue;
      }
    }

    if (ch === '<') {
      const auto = parseAutolink(src, i);
      if (auto) {
        flush();
        nodes.push(auto.node);
        i = auto.end;
        continue;
      }
    }

    if (ch === '*' || ch === '_' || ch === '~') {
      flush();
      const run = runLength(src, i, ch);
      nodes.push(makeDelimiter(src, i, run));
      i += run;
      continue;
    }

    if (ch === '\n') {
      // Two or more trailing spaces before a newline = hard line break.
      const trailing = /( *)$/.exec(text)[1].length;
      text = text.slice(0, text.length - trailing);
      if (trailing >= 2) {
        flush();
        nodes.push({ type: 'break' });
      } else {
        text += '\n'; // soft break: rendered as whitespace
      }
      i++;
      while (src[i] === ' ') i++;
      continue;
    }

    text += ch;
    i++;
  }

  flush();
  return mergeText(processEmphasis(nodes));
}

/** Concatenate the text content of inline nodes (used for alt text and slugs). */
export function plainText(nodes) {
  let out = '';
  for (const n of nodes) {
    if (n.type === 'text' || n.type === 'code') out += n.value;
    else if (n.type === 'image') out += n.alt;
    else if (n.type === 'break') out += ' ';
    else if (n.children) out += plainText(n.children);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Scanner helpers
// ---------------------------------------------------------------------------

function runLength(src, i, ch) {
  let j = i;
  while (src[j] === ch) j++;
  return j - i;
}

function unescapePunct(s) {
  return s.replace(/\\([!-/:-@[-`{-~])/g, '$1');
}

function skipSpaces(src, k) {
  let sawNewline = false;
  while (k < src.length) {
    if (src[k] === ' ' || src[k] === '\t') k++;
    else if (src[k] === '\n' && !sawNewline) {
      sawNewline = true;
      k++;
    } else break;
  }
  return k;
}

/** A code span opens with N backticks and closes with exactly N backticks. */
function parseCodeSpan(src, i) {
  const n = runLength(src, i, '`');
  let j = i + n;
  while (j < src.length) {
    const k = src.indexOf('`', j);
    if (k < 0) return null;
    const m = runLength(src, k, '`');
    if (m === n) {
      let code = src.slice(i + n, k).replace(/\n/g, ' ');
      // One leading+trailing space is stripped so `` `x` `` can hold backticks.
      if (code.length >= 2 && code[0] === ' ' && code.at(-1) === ' ' && code.trim() !== '') {
        code = code.slice(1, -1);
      }
      return { node: { type: 'code', value: code }, end: k + m };
    }
    j = k + m;
  }
  return null;
}

/**
 * Parse `[label](destination "title")` starting at the `[` at index i.
 * Brackets in the label may nest; code spans and escapes are skipped so a
 * `]` inside them does not end the label.
 */
function parseLinkLike(src, i) {
  let depth = 0;
  let j = i;
  for (; j < src.length; j++) {
    const c = src[j];
    if (c === '\\') {
      j++;
      continue;
    }
    if (c === '`') {
      const span = parseCodeSpan(src, j);
      j = (span ? span.end : j + runLength(src, j, '`')) - 1;
      continue;
    }
    if (c === '[') depth++;
    else if (c === ']') {
      depth--;
      if (depth === 0) break;
    }
  }
  if (j >= src.length || src[j + 1] !== '(') return null;

  const dest = parseDestination(src, j + 2);
  if (!dest) return null;
  return { label: src.slice(i + 1, j), dest: dest.url, title: dest.title, end: dest.end };
}

function parseDestination(src, k) {
  k = skipSpaces(src, k);
  let url;
  if (src[k] === '<') {
    const close = src.indexOf('>', k);
    if (close < 0 || src.slice(k + 1, close).includes('\n')) return null;
    url = src.slice(k + 1, close);
    k = close + 1;
  } else {
    // Bare destination: no whitespace, parentheses must balance.
    const start = k;
    let parens = 0;
    while (k < src.length) {
      const c = src[k];
      if (c === '\\' && ESCAPABLE.test(src[k + 1] ?? '')) {
        k += 2;
        continue;
      }
      if (isWhitespace(c)) break;
      if (c === '(') parens++;
      else if (c === ')') {
        if (parens === 0) break;
        parens--;
      }
      k++;
    }
    url = src.slice(start, k);
  }

  const afterUrl = k;
  k = skipSpaces(src, k);
  let title = null;
  const quote = src[k];
  if (k > afterUrl && (quote === '"' || quote === "'" || quote === '(')) {
    const closeCh = quote === '(' ? ')' : quote;
    let end = k + 1;
    while (end < src.length && src[end] !== closeCh) end += src[end] === '\\' ? 2 : 1;
    if (end >= src.length) return null;
    title = unescapePunct(src.slice(k + 1, end));
    k = skipSpaces(src, end + 1);
  }
  if (src[k] !== ')') return null;
  return { url: unescapePunct(url), title, end: k + 1 };
}

const URI_AUTOLINK = /^<([a-zA-Z][a-zA-Z0-9+.-]{1,31}:[^\s<>]*)>/;
const EMAIL_AUTOLINK =
  /^<([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)>/;

function parseAutolink(src, i) {
  const rest = src.slice(i);
  let m = URI_AUTOLINK.exec(rest);
  if (m) {
    return {
      node: { type: 'link', href: m[1], title: null, children: [{ type: 'text', value: m[1] }] },
      end: i + m[0].length,
    };
  }
  m = EMAIL_AUTOLINK.exec(rest);
  if (m) {
    return {
      node: { type: 'link', href: `mailto:${m[1]}`, title: null, children: [{ type: 'text', value: m[1] }] },
      end: i + m[0].length,
    };
  }
  return null;
}

// ---------------------------------------------------------------------------
// Emphasis (delimiter run algorithm)
// ---------------------------------------------------------------------------

/**
 * A delimiter run is *left-flanking* if it is not followed by whitespace and
 * either not followed by punctuation or preceded by whitespace/punctuation.
 * Right-flanking is the mirror image. `_` adds an intraword restriction so
 * snake_case_names are not emphasised.
 */
function makeDelimiter(src, i, run) {
  const ch = src[i];
  const before = i === 0 ? ' ' : src[i - 1];
  const after = i + run >= src.length ? ' ' : src[i + run];
  const left = !isWhitespace(after) && (!isPunct(after) || isWhitespace(before) || isPunct(before));
  const right = !isWhitespace(before) && (!isPunct(before) || isWhitespace(after) || isPunct(after));

  let canOpen = left;
  let canClose = right;
  if (ch === '_') {
    canOpen = left && (!right || isPunct(before));
    canClose = right && (!left || isPunct(after));
  } else if (ch === '~') {
    // GFM strikethrough: we accept exactly two tildes.
    canOpen = left && run === 2;
    canClose = right && run === 2;
  }
  return { type: 'delim', char: ch, count: run, origCount: run, canOpen, canClose };
}

function canPair(opener, closer) {
  if (opener.type !== 'delim' || opener.char !== closer.char || !opener.canOpen) return false;
  if (closer.char === '~') return opener.count >= 2 && closer.count >= 2;
  // "Rule of 3": if either run could both open and close, the sum of the
  // original run lengths must not be a multiple of 3 (unless both are).
  if (
    (opener.canClose || closer.canOpen) &&
    (opener.origCount + closer.origCount) % 3 === 0 &&
    !(opener.origCount % 3 === 0 && closer.origCount % 3 === 0)
  ) {
    return false;
  }
  return true;
}

const delimToText = (n) => (n.type === 'delim' ? { type: 'text', value: n.char.repeat(n.count) } : n);

function processEmphasis(nodes) {
  let ci = 0;
  while (ci < nodes.length) {
    const closer = nodes[ci];
    if (closer.type !== 'delim' || !closer.canClose) {
      ci++;
      continue;
    }

    let oi = ci - 1;
    while (oi >= 0 && !canPair(nodes[oi], closer)) oi--;
    if (oi < 0) {
      ci++;
      continue;
    }

    const opener = nodes[oi];
    const use = closer.char === '~' ? 2 : opener.count >= 2 && closer.count >= 2 ? 2 : 1;
    const type = closer.char === '~' ? 'del' : use === 2 ? 'strong' : 'em';
    // Delimiters between a matched pair can no longer match anything.
    const children = mergeText(nodes.slice(oi + 1, ci).map(delimToText));
    const wrapped = { type, children };

    opener.count -= use;
    closer.count -= use;
    const replacement = [];
    if (opener.count > 0) replacement.push(opener);
    replacement.push(wrapped);
    if (closer.count > 0) replacement.push(closer);
    nodes.splice(oi, ci - oi + 1, ...replacement);

    // Revisit the closer if it still has delimiters left (e.g. `***a***`).
    ci = oi + replacement.indexOf(wrapped) + 1;
  }
  return nodes.map(delimToText);
}

function mergeText(nodes) {
  const out = [];
  for (const n of nodes) {
    const prev = out.at(-1);
    if (n.type === 'text' && prev && prev.type === 'text') prev.value += n.value;
    else out.push(n.type === 'text' ? { ...n } : n);
  }
  return out;
}
