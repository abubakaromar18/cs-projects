/**
 * HTML templates. Plain template literals keep the dependency list short;
 * every user-supplied value passes through escapeHtml() before interpolation.
 */
import { escapeHtml as e } from './highlight.js';
import { EXPIRY_CHOICES, describeRemaining } from './expiry.js';
import { POPULAR_LANGUAGES } from './highlight.js';

function layout(title, body) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${e(title)} · Pastebin</title>
  <link rel="stylesheet" href="/static/hljs.css">
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <header><a href="/" class="brand">Pastebin</a></header>
  <main>${body}</main>
</body>
</html>`;
}

export function homePage({ recent, now, error = null, values = {} }) {
  const langOptions = POPULAR_LANGUAGES.map(
    (l) => `<option value="${l}"${values.language === l ? ' selected' : ''}>${l}</option>`,
  ).join('');
  const expiryOptions = EXPIRY_CHOICES.map(
    ({ value, label }) =>
      `<option value="${value}"${(values.expiresIn ?? '1d') === value ? ' selected' : ''}>${label}</option>`,
  ).join('');
  const recentList = recent.length
    ? `<ul class="recent">${recent
        .map(
          (p) => `<li><a href="/${p.id}">${e(p.title || p.id)}</a>
            <span class="muted">${e(p.language)} · expires ${describeRemaining(p.expiresAt, now)}</span></li>`,
        )
        .join('')}</ul>`
    : '<p class="muted">No public pastes yet.</p>';

  return layout(
    'New paste',
    `
    ${error ? `<p class="error">${e(error)}</p>` : ''}
    <form method="post" action="/pastes" class="paste-form">
      <input name="title" placeholder="Title (optional)" maxlength="100" value="${e(values.title ?? '')}">
      <textarea name="content" rows="18" required placeholder="Paste your code here…">${e(values.content ?? '')}</textarea>
      <div class="row">
        <label>Language <select name="language">${langOptions}</select></label>
        <label>Expires <select name="expiresIn">${expiryOptions}</select></label>
        <label><input type="checkbox" name="burnAfterRead" value="1"${values.burnAfterRead ? ' checked' : ''}> Burn after reading</label>
        <button type="submit">Create paste</button>
      </div>
    </form>
    <h2>Recent pastes</h2>
    ${recentList}`,
  );
}

export function pastePage({ paste, highlighted, now }) {
  const lines = highlighted.html.split('\n');
  const gutter = lines.map((_, i) => `<span>${i + 1}</span>`).join('\n');
  return layout(
    paste.title || paste.id,
    `
    <div class="meta">
      <h1>${e(paste.title || 'Untitled paste')}</h1>
      <span class="muted">${e(highlighted.language)} · ${paste.views} view${paste.views === 1 ? '' : 's'} ·
        expires ${describeRemaining(paste.expiresAt, now)}</span>
      ${paste.burnAfterRead ? '<p class="warn">This paste was set to burn after reading and has now been deleted.</p>' : ''}
      ${paste.burnAfterRead ? '' : `<a href="/raw/${paste.id}">raw</a>`}
    </div>
    <pre class="code"><code class="gutter" aria-hidden="true">${gutter}</code><code class="hljs">${highlighted.html}</code></pre>`,
  );
}

export function createdPage({ paste, baseUrl }) {
  const url = `${baseUrl}/${paste.id}`;
  return layout(
    'Paste created',
    `
    <h1>Paste created</h1>
    <p>This paste will be deleted the first time someone opens it. Share this link once:</p>
    <p><code class="link">${e(url)}</code></p>
    <p class="muted">Opening it yourself will burn it.</p>`,
  );
}

export function notFoundPage() {
  return layout(
    'Not found',
    `<h1>Paste not found</h1>
     <p>It may have expired, been burned after reading, or never existed.</p>
     <p><a href="/">Create a new paste</a></p>`,
  );
}
