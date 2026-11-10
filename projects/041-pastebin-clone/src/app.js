/**
 * Express application factory.
 *
 * `createApp()` builds the app around an injected PasteStore so tests can use
 * a store with a fake clock; `server.js` wires it to a real port.
 */
import express from 'express';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import { PasteStore, StoreFullError } from './store.js';
import { parseExpiry } from './expiry.js';
import { highlight, normalizeLanguage } from './highlight.js';
import { isValidId } from './ids.js';
import * as views from './views.js';

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));

export const MAX_CONTENT_BYTES = 512 * 1024; // 512 KiB per paste
const MAX_TITLE_LENGTH = 100;

/** Raised for bad client input; mapped to HTTP 400. */
class ValidationError extends Error {}

/** Validate and normalise a create-paste request body (JSON or form). */
export function parsePasteInput(body = {}) {
  const content = typeof body.content === 'string' ? body.content : '';
  if (content.trim() === '') throw new ValidationError('Content must not be empty.');
  if (Buffer.byteLength(content, 'utf8') > MAX_CONTENT_BYTES) {
    throw new ValidationError(`Content exceeds ${MAX_CONTENT_BYTES / 1024} KiB.`);
  }
  const title = typeof body.title === 'string' ? body.title.trim().slice(0, MAX_TITLE_LENGTH) : '';

  let ttlMs;
  try {
    ttlMs = parseExpiry(body.expiresIn);
  } catch (err) {
    throw new ValidationError(err.message);
  }

  // Forms send "1"/"on"; JSON sends a boolean.
  const burn = body.burnAfterRead;
  const burnAfterRead = burn === true || burn === '1' || burn === 'on' || burn === 'true';

  return { content, title, language: normalizeLanguage(body.language), ttlMs, burnAfterRead };
}

/** Public JSON shape of a paste — never includes the delete token. */
function toJson(paste, baseUrl) {
  return {
    id: paste.id,
    title: paste.title,
    language: paste.language,
    content: paste.content,
    createdAt: new Date(paste.createdAt).toISOString(),
    expiresAt: paste.expiresAt === null ? null : new Date(paste.expiresAt).toISOString(),
    burnAfterRead: paste.burnAfterRead,
    views: paste.views,
    url: `${baseUrl}/${paste.id}`,
    rawUrl: `${baseUrl}/raw/${paste.id}`,
  };
}

/**
 * @param {object} [opts]
 * @param {PasteStore} [opts.store]
 * @param {number} [opts.sweepIntervalMs] 0 disables the background sweeper
 */
export function createApp({ store = new PasteStore(), sweepIntervalMs = 0 } = {}) {
  const app = express();
  app.disable('x-powered-by');
  app.locals.store = store;

  if (sweepIntervalMs > 0) {
    // unref() so the timer never keeps the process alive on shutdown.
    const timer = setInterval(() => store.sweep(), sweepIntervalMs);
    timer.unref();
    app.locals.sweeper = timer;
  }

  // Defensive headers: no inline scripts or third-party resources are needed.
  app.use((req, res, next) => {
    res.set({
      'Content-Security-Policy': "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
    });
    next();
  });

  const limit = `${MAX_CONTENT_BYTES + 16 * 1024}b`; // headroom for other fields
  app.use(express.json({ limit }));
  app.use(express.urlencoded({ extended: false, limit }));

  // Static assets: our stylesheet plus a highlight.js theme from node_modules.
  app.get('/static/hljs.css', (req, res) => {
    res.type('text/css').sendFile(require.resolve('highlight.js/styles/github.css'));
  });
  app.use('/static', express.static(path.join(HERE, '..', 'public'), { maxAge: '1h' }));

  const baseUrl = (req) => `${req.protocol}://${req.get('host')}`;

  // ---------- JSON API ----------

  app.get('/healthz', (req, res) => res.json({ ok: true, pastes: store.size }));

  app.post('/api/pastes', (req, res) => {
    const input = parsePasteInput(req.body);
    const paste = store.create(input);
    res
      .status(201)
      .location(`/api/pastes/${paste.id}`)
      .json({ ...toJson(paste, baseUrl(req)), deleteToken: paste.deleteToken });
  });

  app.get('/api/pastes/:id', (req, res) => {
    const paste = isValidId(req.params.id) ? store.view(req.params.id) : null;
    if (!paste) return res.status(404).json({ error: 'Paste not found' });
    res.json(toJson(paste, baseUrl(req)));
  });

  app.delete('/api/pastes/:id', (req, res) => {
    const token = req.get('X-Delete-Token');
    const outcome = isValidId(req.params.id) ? store.deleteWithToken(req.params.id, token) : 'not_found';
    if (outcome === 'not_found') return res.status(404).json({ error: 'Paste not found' });
    if (outcome === 'forbidden') return res.status(403).json({ error: 'Invalid delete token' });
    res.status(204).end();
  });

  // ---------- HTML pages ----------

  app.get('/', (req, res) => {
    res.send(views.homePage({ recent: store.recent(10), now: store.now() }));
  });

  app.post('/pastes', (req, res) => {
    let input;
    try {
      input = parsePasteInput(req.body);
    } catch (err) {
      if (!(err instanceof ValidationError)) throw err;
      return res
        .status(400)
        .send(views.homePage({ recent: store.recent(10), now: store.now(), error: err.message, values: req.body }));
    }
    const paste = store.create(input);
    // Redirecting a burn-after-read paste to its page would burn it at once,
    // so show the share link instead.
    if (paste.burnAfterRead) {
      return res.status(201).send(views.createdPage({ paste, baseUrl: baseUrl(req) }));
    }
    res.redirect(303, `/${paste.id}`);
  });

  app.get('/raw/:id', (req, res) => {
    const paste = isValidId(req.params.id) ? store.view(req.params.id) : null;
    if (!paste) return res.status(404).type('text/plain').send('Paste not found\n');
    res.type('text/plain; charset=utf-8').send(paste.content);
  });

  app.get('/:id', (req, res, next) => {
    if (!isValidId(req.params.id)) return next();
    const paste = store.view(req.params.id);
    if (!paste) return res.status(404).send(views.notFoundPage());
    const highlighted = highlight(paste.content, paste.language);
    res.set('Cache-Control', 'no-store').send(views.pastePage({ paste, highlighted, now: store.now() }));
  });

  // ---------- Fallbacks ----------

  app.use((req, res) => {
    if (req.path.startsWith('/api/')) return res.status(404).json({ error: 'Not found' });
    res.status(404).send(views.notFoundPage());
  });

  // Express 4 forwards synchronous throws here.
  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    let status = 500;
    let message = 'Internal server error';
    if (err instanceof ValidationError) [status, message] = [400, err.message];
    else if (err instanceof StoreFullError) [status, message] = [503, err.message];
    else if (err.type === 'entity.too.large') [status, message] = [413, 'Request body too large'];
    else if (err.type === 'entity.parse.failed') [status, message] = [400, 'Malformed JSON'];
    else console.error(err);
    res.status(status).json({ error: message });
  });

  return app;
}
