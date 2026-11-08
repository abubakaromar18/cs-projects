import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [
		sveltekit({
			adapter: adapter(),
			// The public origin is fixed at build time. SvelteKit compares it with
			// each form post's Origin header to block cross-site requests.
			paths: { origin: process.env.ORIGIN ?? 'http://localhost:3000' },
			// `auto` hashes SvelteKit's inline bootstrap script, so no script from
			// user content could run even if an escaping bug slipped through.
			csp: {
				mode: 'auto',
				directives: {
					'default-src': ['self'],
					'script-src': ['self'],
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'object-src': ['none'],
					'base-uri': ['self'],
					'form-action': ['self']
				}
			}
		})
	],
	test: { include: ['tests/**/*.test.js'], environment: 'node' }
});
