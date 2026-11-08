/**
 * Edit URLs contain a secret token, so the browser must never send the full
 * URL to another site in a Referer header.
 * @type {import('@sveltejs/kit').Handle}
 */
export async function handle({ event, resolve }) {
	const response = await resolve(event);
	response.headers.set('Referrer-Policy', 'same-origin');
	response.headers.set('X-Content-Type-Options', 'nosniff');
	return response;
}
