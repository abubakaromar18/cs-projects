<script>
	import { untrack } from 'svelte';
	import { enhance } from '$app/forms';
	import { page as appPage } from '$app/state';
	import ProfileCard from '#lib/components/ProfileCard.svelte';
	import { LIMITS, moveItem } from '#lib/profile.js';
	import { THEMES } from '#lib/themes.js';

	let { data, form } = $props();

	// `key` is local-only: it keeps rows stable before a link has a server id.
	let nextKey = 0;
	const withKeys = (list) => list.map((link) => ({ ...link, key: nextKey++ }));

	// The form owns these once loaded; server data only seeds them.
	const initial = untrack(() => data.page);
	let displayName = $state(initial.displayName);
	let bio = $state(initial.bio);
	let theme = $state(initial.theme);
	let links = $state(withKeys(initial.links));
	let saving = $state(false);
	let dirty = $state(false);

	const errors = $derived(form?.errors ?? {});
	const linksJson = $derived(JSON.stringify(links.map(({ id, title, url }) => ({ id, title, url }))));
	const totalClicks = $derived(links.reduce((sum, link) => sum + (link.clicks ?? 0), 0));
	const publicPath = $derived(`/${data.page.slug}`);

	function addLink() {
		links.push({ key: nextKey++, id: '', title: '', url: '', clicks: 0 });
		dirty = true;
	}

	function removeLink(index) {
		links.splice(index, 1);
		dirty = true;
	}

	function move(index, offset) {
		links = moveItem(links, index, index + offset);
		dirty = true;
	}

	function submit() {
		saving = true;
		return async ({ result, update }) => {
			// reset:false: inputs are bound to state, which already holds the values.
			await update({ reset: false, invalidateAll: false });
			if (result.type === 'success' && result.data?.links) {
				links = withKeys(result.data.links);
				dirty = false;
			}
			saving = false;
		};
	}
</script>

<svelte:head>
	<title>Edit {data.page.displayName} · Linkpage</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="editor">
	<div class="column">
		<header class="editor-head">
			<h1>Edit your page</h1>
			<a class="button secondary" href={publicPath} target="_blank" rel="noopener">View page</a>
		</header>

		{#if appPage.url.searchParams.has('new')}
			<p class="notice"><strong>Bookmark this page.</strong> Its address is the only way to edit your page.</p>
		{/if}

		<p class="muted">
			Live at <a href={publicPath}>{appPage.url.origin}{publicPath}</a> ·
			{totalClicks} {totalClicks === 1 ? 'click' : 'clicks'}
		</p>

		<form class="panel" method="POST" use:enhance={submit} oninput={() => (dirty = true)}>
			<input type="hidden" name="links" value={linksJson} />

			<label>
				Display name
				<input name="displayName" required maxlength={LIMITS.displayName} bind:value={displayName} />
				{#if errors.displayName}<small class="error">{errors.displayName}</small>{/if}
			</label>

			<label>
				Bio
				<textarea name="bio" rows="2" maxlength={LIMITS.bio} bind:value={bio}></textarea>
				<small class="muted">{[...bio].length}/{LIMITS.bio}</small>
				{#if errors.bio}<small class="error">{errors.bio}</small>{/if}
			</label>

			<fieldset>
				<legend>Theme</legend>
				<div class="themes">
					{#each THEMES as option (option.id)}
						<label class="theme-option" data-theme={option.id}>
							<input type="radio" name="theme" value={option.id} bind:group={theme} />
							{option.label}
						</label>
					{/each}
				</div>
				{#if errors.theme}<small class="error">{errors.theme}</small>{/if}
			</fieldset>

			<fieldset>
				<legend>Links</legend>
				{#if errors.links}<small class="error">{errors.links}</small>{/if}

				{#each links as link, i (link.key)}
					<div class="link-row">
						<div class="link-fields">
							<input aria-label={`Link ${i + 1} title`} placeholder="Title" maxlength={LIMITS.linkTitle} bind:value={link.title} />
							{#if errors[`links.${i}.title`]}<small class="error">{errors[`links.${i}.title`]}</small>{/if}
							<input aria-label={`Link ${i + 1} address`} placeholder="example.com" inputmode="url" spellcheck="false" bind:value={link.url} />
							{#if errors[`links.${i}.url`]}<small class="error">{errors[`links.${i}.url`]}</small>{/if}
							{#if link.id}<small class="muted">{link.clicks} {link.clicks === 1 ? 'click' : 'clicks'}</small>{/if}
						</div>
						<div class="row-actions">
							<button type="button" aria-label={`Move link ${i + 1} up`} disabled={i === 0} onclick={() => move(i, -1)}>↑</button>
							<button type="button" aria-label={`Move link ${i + 1} down`} disabled={i === links.length - 1} onclick={() => move(i, 1)}>↓</button>
							<button type="button" aria-label={`Remove link ${i + 1}`} onclick={() => removeLink(i)}>✕</button>
						</div>
					</div>
				{/each}

				<button class="button secondary" type="button" disabled={links.length >= LIMITS.links} onclick={addLink}>Add link</button>
			</fieldset>

			<div class="save-row">
				<button class="button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
				<span role="status" class="muted">
					{#if dirty}Unsaved changes{:else if form?.saved}Saved{/if}
				</span>
			</div>
		</form>
	</div>

	<aside class="preview" aria-label="Live preview">
		<ProfileCard {displayName} {bio} {theme} {links} interactive={false} />
	</aside>
</main>
