import { fail, redirect } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { SlugTakenError } from '#lib/server/store.js';
import { createEditToken, hashToken } from '#lib/server/tokens.js';
import { validateProfile, validateSlug } from '#lib/profile.js';
import { DEFAULT_THEME } from '#lib/themes.js';

/** @type {import('./$types').Actions} */
export const actions = {
	default: async ({ request }) => {
		const form = await request.formData();
		const values = { slug: String(form.get('slug') ?? ''), displayName: String(form.get('displayName') ?? '') };

		const slug = validateSlug(values.slug);
		const profile = validateProfile({
			displayName: values.displayName,
			bio: '',
			theme: DEFAULT_THEME,
			links: []
		});

		if (!slug.ok || !profile.ok) {
			return fail(400, {
				values,
				errors: {
					...(slug.ok ? {} : { slug: slug.error }),
					...(profile.ok ? {} : profile.errors)
				}
			});
		}

		const token = createEditToken();
		try {
			await db.create({ slug: slug.value, tokenHash: hashToken(token), profile: profile.value });
		} catch (err) {
			if (err instanceof SlugTakenError) {
				return fail(409, { values, errors: { slug: 'That address is already taken.' } });
			}
			throw err;
		}

		redirect(303, `/edit/${token}?new=1`);
	}
};
