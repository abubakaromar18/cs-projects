import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { SlugTakenError, createStore, mergeLinks } from '../src/lib/server/store.js';
import { createEditToken, hashToken } from '../src/lib/server/tokens.js';

const profile = (links = []) => ({ displayName: 'Ada', bio: '', theme: 'paper', links });
const link = (id, title = 'T') => ({ id, title, url: 'https://example.com/' });

describe('store', () => {
	let dir, file, store;

	beforeEach(async () => {
		dir = await mkdtemp(join(tmpdir(), 'linkpage-'));
		file = join(dir, 'nested', 'pages.json');
		store = createStore(file);
	});
	afterEach(() => rm(dir, { recursive: true, force: true }));

	it('creates and finds pages', async () => {
		await store.create({ slug: 'ada', tokenHash: 'h', profile: profile() });
		expect((await store.getBySlug('ada')).displayName).toBe('Ada');
		expect((await store.getByTokenHash('h')).slug).toBe('ada');
		expect(await store.getBySlug('nobody')).toBeNull();
		expect(await store.getByTokenHash('nope')).toBeNull();
	});

	it('allows only one winner when a slug is raced', async () => {
		const results = await Promise.allSettled(
			Array.from({ length: 10 }, (_, i) => store.create({ slug: 'ada', tokenHash: `h${i}`, profile: profile() }))
		);
		expect(results.filter((r) => r.status === 'fulfilled')).toHaveLength(1);
		expect(results.filter((r) => r.reason instanceof SlugTakenError)).toHaveLength(9);
	});

	it('keeps working after a failed mutation', async () => {
		await store.create({ slug: 'ada', tokenHash: 'h', profile: profile() });
		await expect(store.create({ slug: 'ada', tokenHash: 'h', profile: profile() })).rejects.toThrow(SlugTakenError);
		await expect(store.create({ slug: 'bob', tokenHash: 'i', profile: profile() })).resolves.toBeTruthy();
	});

	it('does not lose concurrent clicks', async () => {
		const created = await store.create({ slug: 'ada', tokenHash: 'h', profile: profile([link('')]) });
		const id = created.links[0].id;
		await Promise.all(Array.from({ length: 50 }, () => store.recordClick('ada', id)));

		const reloaded = createStore(file);
		expect((await reloaded.getBySlug('ada')).links[0].clicks).toBe(50);
	});

	it('returns null for unknown clicks', async () => {
		await store.create({ slug: 'ada', tokenHash: 'h', profile: profile() });
		expect(await store.recordClick('ada', 'missing')).toBeNull();
		expect(await store.recordClick('nobody', 'missing')).toBeNull();
	});

	it('hands out copies, not internal state', async () => {
		await store.create({ slug: 'ada', tokenHash: 'h', profile: profile() });
		(await store.getBySlug('ada')).displayName = 'Mallory';
		expect((await store.getBySlug('ada')).displayName).toBe('Ada');
	});

	it('leaves no temp files', async () => {
		await store.create({ slug: 'ada', tokenHash: 'h', profile: profile() });
		expect(await readdir(join(dir, 'nested'))).toEqual(['pages.json']);
		expect(JSON.parse(await readFile(file, 'utf8'))).toHaveLength(1);
	});

	it('refuses to treat a corrupt file as empty', async () => {
		const corrupt = join(dir, 'corrupt.json');
		await writeFile(corrupt, '{oops');
		await expect(createStore(corrupt).getBySlug('ada')).rejects.toThrow(SyntaxError);
		expect(await readFile(corrupt, 'utf8')).toBe('{oops');
	});

	it('updates a page and keeps click counts through a reorder', async () => {
		const created = await store.create({ slug: 'ada', tokenHash: 'h', profile: profile([link('', 'A'), link('', 'B')]) });
		const [a, b] = created.links;
		await store.recordClick('ada', b.id);

		const updated = await store.update('ada', { ...profile([link(b.id, 'B2'), link(a.id, 'A')]), displayName: 'Ada L' });
		expect(updated.displayName).toBe('Ada L');
		expect(updated.tokenHash).toBe('h');
		expect(updated.links.map((l) => [l.title, l.clicks])).toEqual([['B2', 1], ['A', 0]]);
	});
});

describe('mergeLinks', () => {
	const existing = [{ id: 'keep', title: 'K', url: 'u', clicks: 5 }];

	it('replaces unknown ids and starts at zero clicks', () => {
		const [merged] = mergeLinks(existing, [{ id: 'forged', title: 'F', url: 'u', clicks: 999 }]);
		expect(merged.id).not.toBe('forged');
		expect(merged.clicks).toBe(0);
	});
	it('honours a duplicated id only once', () => {
		const merged = mergeLinks(existing, [link('keep'), link('keep')]);
		expect(merged[0].id).toBe('keep');
		expect(merged[1].id).not.toBe('keep');
		expect(merged[1].clicks).toBe(0);
	});
});

describe('tokens', () => {
	it('are unique, URL-safe and hash deterministically', () => {
		const a = createEditToken();
		expect(a).toMatch(/^[\w-]{32}$/);
		expect(a).not.toBe(createEditToken());
		expect(hashToken(a)).toBe(hashToken(a));
		expect(hashToken(a)).not.toBe(a);
	});
});
