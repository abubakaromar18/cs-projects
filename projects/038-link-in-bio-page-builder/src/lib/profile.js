// Validation and small pure helpers, shared by the server and the editor.
// The server is the only authority: everything is re-checked in form actions.
import { THEMES } from './themes.js';

export const LIMITS = Object.freeze({
	displayName: 50,
	bio: 160,
	linkTitle: 60,
	url: 2048,
	links: 20
});

const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{1,28})[a-z0-9]$/;

/** Slugs that would be confusing or collide with top-level app routes. */
export const RESERVED_SLUGS = new Set([
	'about', 'admin', 'api', 'app', 'assets', 'edit', 'favicon', 'help',
	'login', 'new', 'robots', 'settings', 'signup', 'static', 'support'
]);

/**
 * @param {unknown} raw
 * @returns {{ ok: true, value: string } | { ok: false, error: string }}
 */
export function validateSlug(raw) {
	const value = String(raw ?? '').trim().toLowerCase();
	if (!SLUG_PATTERN.test(value)) {
		return {
			ok: false,
			error: 'Use 3–30 lowercase letters, numbers or hyphens, starting and ending with a letter or number.'
		};
	}
	if (RESERVED_SLUGS.has(value)) return { ok: false, error: 'That address is reserved.' };
	return { ok: true, value };
}

/**
 * Normalize a user-supplied link to an absolute http(s) URL.
 *
 * This allow-list is the core XSS defence for links: `javascript:` and `data:`
 * URLs would otherwise execute when a visitor clicks them. It returns null for
 * anything else.
 * @param {unknown} raw
 * @returns {string | null}
 */
export function normalizeUrl(raw) {
	const input = String(raw ?? '').trim();
	if (!input || input.length > LIMITS.url) return null;

	// "example.com" and "example.com:8080/x" have no scheme, so assume https.
	const hasScheme = /^[a-z][a-z0-9+.-]*:/i.test(input) && !/^[^/:]+:\d+(?:[/?#]|$)/.test(input);
	let url;
	try {
		url = new URL(hasScheme ? input : `https://${input}`);
	} catch {
		return null;
	}

	if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
	// "https://bank.com@evil.test" reads like bank.com but goes to evil.test.
	if (url.username || url.password) return null;
	if (!url.hostname.includes('.') && url.hostname !== 'localhost') return null;
	return url.href;
}

/**
 * Validate a full profile. Errors are keyed by field, with `links.N.title` and
 * `links.N.url` for individual rows, so the editor can show them inline.
 * @param {{ displayName?: unknown, bio?: unknown, theme?: unknown, links?: unknown }} input
 */
export function validateProfile(input) {
	/** @type {Record<string, string>} */
	const errors = {};

	const displayName = String(input.displayName ?? '').trim();
	if (!displayName) errors.displayName = 'Add a display name.';
	else if ([...displayName].length > LIMITS.displayName) {
		errors.displayName = `Keep it to ${LIMITS.displayName} characters.`;
	}

	const bio = String(input.bio ?? '').trim();
	if ([...bio].length > LIMITS.bio) errors.bio = `Keep it to ${LIMITS.bio} characters.`;

	const theme = String(input.theme ?? '');
	if (!THEMES.some((t) => t.id === theme)) errors.theme = 'Choose one of the available themes.';

	const rawLinks = Array.isArray(input.links) ? input.links : [];
	if (rawLinks.length > LIMITS.links) errors.links = `You can add up to ${LIMITS.links} links.`;

	const links = rawLinks.slice(0, LIMITS.links).map((link, i) => {
		const title = String(link?.title ?? '').trim();
		if (!title) errors[`links.${i}.title`] = 'Add a title.';
		else if ([...title].length > LIMITS.linkTitle) {
			errors[`links.${i}.title`] = `Keep it to ${LIMITS.linkTitle} characters.`;
		}

		const url = normalizeUrl(link?.url);
		if (!url) errors[`links.${i}.url`] = 'Enter a valid http or https address.';

		return { id: String(link?.id ?? ''), title, url: url ?? '' };
	});

	if (Object.keys(errors).length > 0) return { ok: false, errors };
	return { ok: true, value: { displayName, bio, theme, links } };
}

/**
 * Parse the editor's JSON-encoded link list.
 * @param {unknown} raw
 * @returns {unknown[] | null} null when the payload is not a JSON array
 */
export function parseLinks(raw) {
	try {
		const parsed = JSON.parse(String(raw ?? '[]'));
		return Array.isArray(parsed) ? parsed : null;
	} catch {
		return null;
	}
}

/**
 * Up to two initials for the generated avatar. Spreading the string keeps
 * emoji and other astral characters whole.
 * @param {string} name
 */
export function initials(name) {
	const words = name.trim().split(/\s+/).filter(Boolean);
	if (words.length === 0) return '?';
	const picked = words.length === 1 ? [words[0]] : [words[0], words[words.length - 1]];
	return picked.map((w) => [...w][0]).join('').toUpperCase();
}

/**
 * Return a copy of `items` with one element moved; out-of-range moves are no-ops.
 * @template T
 * @param {T[]} items
 * @param {number} from
 * @param {number} to
 * @returns {T[]}
 */
export function moveItem(items, from, to) {
	const copy = [...items];
	if (from < 0 || from >= copy.length || to < 0 || to >= copy.length) return copy;
	const [item] = copy.splice(from, 1);
	copy.splice(to, 0, item);
	return copy;
}
