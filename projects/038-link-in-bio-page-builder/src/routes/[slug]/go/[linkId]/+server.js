import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';

/**
 * Count a click, then send the visitor on. The destination comes only from the
 * store, where it was validated, so this cannot act as an open redirect. It is
 * a plain Response because SvelteKit's redirect() is for internal paths.
 * @type {import('./$types').RequestHandler}
 */
export async function GET({ params }) {
	const url = await db.recordClick(params.slug, params.linkId);
	if (!url) error(404, 'Not found');
	return new Response(null, {
		status: 302,
		// A cached redirect would hide repeat clicks from the counter.
		headers: { location: url, 'cache-control': 'no-store' }
	});
}
