import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params }) {
	const page = await db.getBySlug(params.slug);
	if (!page) error(404, 'Not found');

	// Pick public fields explicitly: tokenHash, click counts and destination
	// URLs stay out of the serialized page data.
	return {
		profile: {
			slug: page.slug,
			displayName: page.displayName,
			bio: page.bio,
			theme: page.theme,
			links: page.links.map(({ id, title }) => ({ id, title }))
		}
	};
}
