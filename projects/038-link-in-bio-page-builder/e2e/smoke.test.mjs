// Black-box test of the production build: a real server, real HTTP, plain
// (no-JavaScript) form posts. Run with `npm run test:e2e`, which builds first.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, before, test } from 'node:test';

// Must match the ORIGIN the test:e2e script builds with.
const PORT = 4173;
const ORIGIN = `http://127.0.0.1:${PORT}`;
let server, dir, dataFile, editPath;

const post = (path, fields, headers = {}) =>
	fetch(ORIGIN + path, {
		method: 'POST',
		redirect: 'manual',
		headers: { accept: 'text/html', origin: ORIGIN, 'content-type': 'application/x-www-form-urlencoded', ...headers },
		body: new URLSearchParams(fields)
	});

before(async () => {
	dir = await mkdtemp(join(tmpdir(), 'linkpage-e2e-'));
	dataFile = join(dir, 'pages.json');
	server = spawn(process.execPath, ['build'], {
		env: { ...process.env, PORT: String(PORT), HOST: '127.0.0.1', DATA_FILE: dataFile },
		stdio: 'inherit'
	});
	for (let i = 0; i < 50; i++) {
		try {
			await fetch(ORIGIN);
			return;
		} catch {
			await new Promise((r) => setTimeout(r, 100));
		}
	}
	throw new Error('server did not start');
});

after(async () => {
	server.kill();
	await rm(dir, { recursive: true, force: true });
});

test('creating a page redirects to a secret edit URL', async () => {
	const res = await post('/', { slug: 'ada-lovelace', displayName: 'Ada <b>Lovelace</b>' });
	assert.equal(res.status, 303);
	editPath = res.headers.get('location').split('?')[0];
	assert.match(editPath, /^\/edit\/[\w-]{32}$/);
});

test('a slug cannot be claimed twice', async () => {
	const res = await post('/', { slug: 'ada-lovelace', displayName: 'Copycat' });
	assert.equal(res.status, 409);
	assert.match(await res.text(), /already taken/);
});

test('an invalid token is a 404', async () => {
	assert.equal((await fetch(`${ORIGIN}/edit/not-a-real-token`)).status, 404);
	const res = await post('/edit/not-a-real-token', { displayName: 'x', theme: 'paper', links: '[]' });
	assert.equal(res.status, 404);
});

test('cross-origin form posts are refused', async () => {
	const res = await post('/', { slug: 'csrf-page', displayName: 'x' }, { origin: 'https://evil.test' });
	assert.equal(res.status, 403);
});

test('javascript: links are rejected', async () => {
	const res = await post(editPath, {
		displayName: 'Ada',
		bio: '',
		theme: 'midnight',
		links: JSON.stringify([{ id: '', title: 'Bad', url: 'javascript:alert(1)' }])
	});
	assert.equal(res.status, 400);
	assert.match(await res.text(), /valid http or https/);
});

test('publishing, escaping, headers and click counting work together', async () => {
	const saved = await post(editPath, {
		displayName: 'Ada <b>Lovelace</b>',
		bio: 'First programmer',
		theme: 'midnight',
		links: JSON.stringify([{ id: '', title: 'Notes', url: 'example.com/notes' }])
	});
	assert.equal(saved.status, 200);

	const page = await fetch(`${ORIGIN}/ada-lovelace`);
	assert.equal(page.status, 200);
	assert.equal(page.headers.get('referrer-policy'), 'same-origin');
	assert.match(page.headers.get('content-security-policy'), /script-src 'self'/);

	const html = await page.text();
	assert.ok(!html.includes('<b>Lovelace'), 'display name must be escaped');
	assert.ok(!html.includes('tokenHash'), 'token hash must not reach the browser');
	assert.ok(!html.includes(editPath), 'edit link must not be public');

	const href = html.match(/href="(\/ada-lovelace\/go\/[^"]+)"/)[1];
	const click = await fetch(ORIGIN + href, { redirect: 'manual' });
	assert.equal(click.status, 302);
	assert.equal(click.headers.get('location'), 'https://example.com/notes');
	assert.equal(click.headers.get('cache-control'), 'no-store');

	const [stored] = JSON.parse(await readFile(dataFile, 'utf8'));
	assert.equal(stored.links[0].clicks, 1);
	assert.ok(!(await readFile(dataFile, 'utf8')).includes(editPath.split('/').pop()), 'raw token must not be stored');
});

test('unknown pages and links are 404s', async () => {
	assert.equal((await fetch(`${ORIGIN}/nobody-here`)).status, 404);
	const res = await fetch(`${ORIGIN}/ada-lovelace/go/missing`, { redirect: 'manual' });
	assert.equal(res.status, 404);
});
