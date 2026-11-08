import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import ProfileCard from '../src/lib/components/ProfileCard.svelte';

const props = { displayName: 'Ada', bio: 'Hi', theme: 'midnight', slug: 'ada', links: [{ id: 'l1', title: 'Site' }] };

describe('ProfileCard', () => {
	it('links through the click counter with a safe rel', () => {
		const { body } = render(ProfileCard, { props });
		expect(body).toContain('href="/ada/go/l1"');
		expect(body).toContain('rel="noopener noreferrer nofollow"');
		expect(body).toContain('data-theme="midnight"');
	});
	it('escapes user content', () => {
		const payload = '<img src=x onerror=alert(1)>';
		const { body } = render(ProfileCard, {
			props: { ...props, displayName: payload, bio: payload, links: [{ id: 'l1', title: payload }] }
		});
		expect(body).not.toContain('<img');
	});
	it('renders no anchors in preview mode', () => {
		const { body } = render(ProfileCard, { props: { ...props, interactive: false } });
		expect(body).not.toContain('<a');
		expect(body).toContain('Site');
	});
});
