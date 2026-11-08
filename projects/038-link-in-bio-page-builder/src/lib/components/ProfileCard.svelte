<script>
	import { initials } from '#lib/profile.js';

	/**
	 * Renders a profile. Used by the public page and, with `interactive` off,
	 * the editor's live preview, so the preview cannot drift from the real page.
	 */
	let { displayName, bio = '', theme, links = [], slug = '', interactive = true } = $props();
</script>

<div class="profile" data-theme={theme}>
	<div class="profile-inner">
		<div class="avatar" aria-hidden="true">{initials(displayName)}</div>
		<h1>{displayName || 'Your name'}</h1>
		{#if bio}<p class="bio">{bio}</p>{/if}

		<ul class="links">
			{#each links as link (link.id || link.key)}
				<li>
					{#if interactive}
						<!-- Reload: /go is a server redirect, not a client-side route. -->
						<a
							class="link"
							href={`/${slug}/go/${link.id}`}
							rel="noopener noreferrer nofollow"
							data-sveltekit-reload
						>
							{link.title}
						</a>
					{:else}
						<span class="link">{link.title || 'Untitled link'}</span>
					{/if}
				</li>
			{/each}
		</ul>
	</div>
</div>
