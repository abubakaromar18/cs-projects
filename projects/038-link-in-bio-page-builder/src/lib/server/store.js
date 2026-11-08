import { randomUUID } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';

export class SlugTakenError extends Error {
	constructor(slug) {
		super(`Slug already taken: ${slug}`);
		this.name = 'SlugTakenError';
	}
}

/**
 * A small JSON-file document store.
 *
 * Reads come from an in-memory Map. Every mutation runs on a promise queue, so
 * concurrent requests cannot interleave, and is persisted by writing a temp
 * file and renaming it, so a crash cannot leave a half-written data file.
 *
 * @param {string} filePath
 */
export function createStore(filePath) {
	/** @type {Promise<Map<string, any>> | null} */
	let loaded = null;
	/** @type {Promise<unknown>} */
	let queue = Promise.resolve();
	let writeCount = 0;

	function load() {
		loaded ??= readFile(filePath, 'utf8').then(
			(text) => new Map(JSON.parse(text).map((page) => [page.slug, page])),
			(err) => {
				// A missing file is a fresh start. Anything else must surface,
				// otherwise the next write would replace the user's data.
				if (err.code === 'ENOENT') return new Map();
				throw err;
			}
		);
		return loaded;
	}

	async function persist(pages) {
		await mkdir(dirname(filePath), { recursive: true });
		const temp = `${filePath}.${process.pid}.${writeCount++}.tmp`;
		await writeFile(temp, JSON.stringify([...pages.values()], null, '\t'));
		await rename(temp, filePath);
	}

	/**
	 * Run a mutation exclusively. A failed task rejects for its caller only and
	 * does not stop tasks queued behind it.
	 * @template T
	 * @param {(pages: Map<string, any>) => T | Promise<T>} task
	 * @returns {Promise<T>}
	 */
	function mutate(task) {
		const run = queue.then(async () => task(await load()));
		queue = run.catch(() => {});
		return run;
	}

	return {
		/** @param {string} slug */
		async getBySlug(slug) {
			const page = (await load()).get(slug);
			return page ? structuredClone(page) : null;
		},

		/** @param {string} tokenHash */
		async getByTokenHash(tokenHash) {
			for (const page of (await load()).values()) {
				if (page.tokenHash === tokenHash) return structuredClone(page);
			}
			return null;
		},

		/** @param {{ slug: string, tokenHash: string, profile: { displayName: string, bio: string, theme: string, links: any[] } }} input */
		create({ slug, tokenHash, profile }) {
			return mutate(async (pages) => {
				if (pages.has(slug)) throw new SlugTakenError(slug);
				const page = { slug, tokenHash, ...profile, links: mergeLinks([], profile.links) };
				pages.set(slug, page);
				await persist(pages);
				return structuredClone(page);
			});
		},

		/**
		 * @param {string} slug
		 * @param {{ displayName: string, bio: string, theme: string, links: any[] }} profile
		 */
		update(slug, profile) {
			return mutate(async (pages) => {
				const page = pages.get(slug);
				if (!page) return null;
				Object.assign(page, profile, { links: mergeLinks(page.links, profile.links) });
				await persist(pages);
				return structuredClone(page);
			});
		},

		/**
		 * Count a click and return the destination, or null for an unknown link.
		 * @param {string} slug
		 * @param {string} linkId
		 * @returns {Promise<string | null>}
		 */
		recordClick(slug, linkId) {
			return mutate(async (pages) => {
				const link = pages.get(slug)?.links.find((l) => l.id === linkId);
				if (!link) return null;
				link.clicks += 1;
				await persist(pages);
				return link.url;
			});
		}
	};
}

/**
 * Apply an edited link list. Ids and click counts are server-owned: a client id
 * only matters if it names a link already on this page, and is otherwise
 * replaced, so a forged payload cannot set counts or reuse another link's id.
 * @param {{ id: string, title: string, url: string, clicks: number }[]} existing
 * @param {{ id: string, title: string, url: string }[]} incoming
 */
export function mergeLinks(existing, incoming) {
	const known = new Map(existing.map((link) => [link.id, link]));
	return incoming.map(({ id, title, url }) => {
		const previous = known.get(id);
		// Deleting from the map means a duplicated id is only honoured once.
		known.delete(id);
		return { id: previous ? previous.id : randomUUID(), title, url, clicks: previous?.clicks ?? 0 };
	});
}
