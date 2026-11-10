import { test } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';

import { createApp, MAX_CONTENT_BYTES } from '../src/app.js';
import { PasteStore } from '../src/store.js';

function setup() {
  let t = Date.UTC(2026, 0, 1);
  const store = new PasteStore({ now: () => t });
  const app = createApp({ store });
  return { app, store, advance: (ms) => { t += ms; } };
}

test('POST /api/pastes creates a paste and returns links + delete token', async () => {
  const { app } = setup();
  const res = await request(app)
    .post('/api/pastes')
    .send({ content: 'print("hi")', title: 'Greeting', language: 'python', expiresIn: '1h' })
    .expect(201);

  assert.match(res.body.id, /^[A-Za-z0-9]{8}$/);
  assert.equal(res.body.title, 'Greeting');
  assert.equal(res.body.language, 'python');
  assert.equal(res.body.expiresAt, '2026-01-01T01:00:00.000Z');
  assert.ok(res.body.deleteToken);
  assert.equal(res.headers.location, `/api/pastes/${res.body.id}`);
  assert.match(res.body.rawUrl, new RegExp(`/raw/${res.body.id}$`));
});

test('GET /api/pastes/:id returns the paste without the delete token', async () => {
  const { app } = setup();
  const { body: created } = await request(app).post('/api/pastes').send({ content: 'abc' });
  const res = await request(app).get(`/api/pastes/${created.id}`).expect(200);
  assert.equal(res.body.content, 'abc');
  assert.equal(res.body.views, 1);
  assert.equal(res.body.deleteToken, undefined);
});

test('validation errors return 400', async () => {
  const { app } = setup();
  let res = await request(app).post('/api/pastes').send({ content: '   ' }).expect(400);
  assert.match(res.body.error, /empty/);
  res = await request(app).post('/api/pastes').send({ content: 'x', expiresIn: 'forever' }).expect(400);
  assert.match(res.body.error, /Invalid expiry/);
  res = await request(app)
    .post('/api/pastes')
    .set('Content-Type', 'application/json')
    .send('{"content":')
    .expect(400);
  assert.equal(res.body.error, 'Malformed JSON');
});

test('oversized content is rejected', async () => {
  const { app } = setup();
  const res = await request(app)
    .post('/api/pastes')
    .send({ content: 'x'.repeat(MAX_CONTENT_BYTES + 1) })
    .expect(400);
  assert.match(res.body.error, /exceeds/);
});

test('pastes expire over HTTP', async () => {
  const { app, advance } = setup();
  const { body } = await request(app).post('/api/pastes').send({ content: 'temp', expiresIn: '10m' });
  await request(app).get(`/raw/${body.id}`).expect(200, 'temp');
  advance(10 * 60 * 1000);
  await request(app).get(`/raw/${body.id}`).expect(404);
  await request(app).get(`/${body.id}`).expect(404);
});

test('burn-after-read paste is served once, then 404', async () => {
  const { app } = setup();
  const { body } = await request(app).post('/api/pastes').send({ content: 'once', burnAfterRead: true });
  const page = await request(app).get(`/${body.id}`).expect(200);
  assert.match(page.text, /burn after reading/);
  await request(app).get(`/${body.id}`).expect(404);
});

test('DELETE requires the correct token', async () => {
  const { app } = setup();
  const { body } = await request(app).post('/api/pastes').send({ content: 'bye' });
  await request(app).delete(`/api/pastes/${body.id}`).set('X-Delete-Token', 'nope').expect(403);
  await request(app).delete(`/api/pastes/${body.id}`).set('X-Delete-Token', body.deleteToken).expect(204);
  await request(app).get(`/api/pastes/${body.id}`).expect(404);
});

test('HTML view highlights code and escapes user content', async () => {
  const { app } = setup();
  const { body } = await request(app)
    .post('/api/pastes')
    .send({ content: 'function f() { return "<img src=x onerror=alert(1)>"; }', title: '<b>xss</b>', language: 'javascript' });
  const res = await request(app).get(`/${body.id}`).expect(200);
  assert.match(res.headers['content-type'], /text\/html/);
  assert.match(res.text, /hljs-keyword/);
  assert.ok(!res.text.includes('<img src=x'), 'code is escaped');
  assert.ok(!res.text.includes('<b>xss</b>'), 'title is escaped');
  assert.match(res.headers['content-security-policy'], /default-src 'none'/);
});

test('raw endpoint serves plain text with nosniff', async () => {
  const { app } = setup();
  const { body } = await request(app).post('/api/pastes').send({ content: '<h1>not html</h1>' });
  const res = await request(app).get(`/raw/${body.id}`).expect(200);
  assert.match(res.headers['content-type'], /text\/plain/);
  assert.equal(res.headers['x-content-type-options'], 'nosniff');
  assert.equal(res.text, '<h1>not html</h1>');
});

test('form submission redirects to the new paste', async () => {
  const { app, store } = setup();
  const res = await request(app)
    .post('/pastes')
    .type('form')
    .send({ content: 'SELECT 1;', language: 'sql', expiresIn: '1d' })
    .expect(303);
  const id = res.headers.location.slice(1);
  assert.equal(store.peek(id).language, 'sql');
});

test('form submission with burn-after-read shows a share page without burning', async () => {
  const { app, store } = setup();
  const res = await request(app)
    .post('/pastes')
    .type('form')
    .send({ content: 'secret', burnAfterRead: '1' })
    .expect(201);
  assert.match(res.text, /Paste created/);
  const id = /\/([A-Za-z0-9]{8})</.exec(res.text)[1];
  assert.equal(store.peek(id).views, 0);
});

test('invalid form submission re-renders the form with an error', async () => {
  const { app } = setup();
  const res = await request(app).post('/pastes').type('form').send({ content: '', title: 'kept' }).expect(400);
  assert.match(res.text, /must not be empty/);
  assert.match(res.text, /value="kept"/);
});

test('home page lists recent pastes; static assets are served', async () => {
  const { app } = setup();
  await request(app).post('/api/pastes').send({ content: 'x', title: 'Listed paste' });
  const home = await request(app).get('/').expect(200);
  assert.match(home.text, /Listed paste/);
  await request(app).get('/static/app.css').expect(200).expect('Content-Type', /css/);
  await request(app).get('/static/hljs.css').expect(200).expect('Content-Type', /css/);
});

test('unknown routes 404 and health check reports size', async () => {
  const { app } = setup();
  await request(app).get('/not-a-valid-id!').expect(404);
  await request(app).get('/api/nope').expect(404);
  const res = await request(app).get('/healthz').expect(200);
  assert.deepEqual(res.body, { ok: true, pastes: 0 });
});
