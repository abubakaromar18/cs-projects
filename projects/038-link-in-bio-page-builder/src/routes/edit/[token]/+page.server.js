import { error, fail } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { hashToken } from '#lib/server/tokens.js';
import { parseLinks, validateProfile } from '#lib/profile.js';

/** @param {string} token */
async function findPage(token) {
	const page = await db.getByTokenHash(hashToken(token));
	if (!page) error(404, 'Not found');
	return page;
}

/** @type {import('./$types').PageServerLoad} */
export async function load({ params }) {
	const { tokenHash: _omitted, ...page } = await findPage(params.token);
	return { page };
}

/** @type {import('./$types').Actions} */
export const actions = {
	default: async ({ params, request }) => {
		const page = await findPage(params.token);
		const form = await request.formData();

		const links = parseLinks(form.get('links'));
		if (!links) return fail(400, { errors: { links: 'The link list could not be read.' } });

		const result = validateProfile({
			displayName: form.get('displayName'),
			bio: form.get('bio'),
			theme: form.get('theme'),
			links
		});
		if (!result.ok) return fail(400, { errors: result.errors });

		const updated = await db.update(page.slug, result.value);
		if (!updated) error(404, 'Not found');
		// New links get their ids here; the editor adopts them after saving.
		return { saved: true, links: updated.links };
	}
};
