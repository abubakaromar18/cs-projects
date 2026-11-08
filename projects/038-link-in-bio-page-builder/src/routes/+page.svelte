<script>
	import { enhance } from '$app/forms';
	import { LIMITS } from '#lib/profile.js';

	let { form } = $props();
</script>

<svelte:head>
	<title>Linkpage · One page for all your links</title>
	<meta name="description" content="Build a simple, shareable page for all your links." />
</svelte:head>

<main class="home">
	<section>
		<p class="eyebrow">Linkpage</p>
		<h1>One page for everything you share.</h1>
		<p class="lede">Pick an address, add your links and choose a look. No account needed.</p>
	</section>

	<form class="panel" method="POST" use:enhance>
		<label>
			Your address
			<span class="prefixed">
				<span>/</span>
				<input
					name="slug"
					required
					minlength="3"
					maxlength="30"
					autocomplete="off"
					autocapitalize="none"
					spellcheck="false"
					placeholder="ada-lovelace"
					value={form?.values?.slug ?? ''}
				/>
			</span>
			{#if form?.errors?.slug}<small class="error">{form.errors.slug}</small>{/if}
		</label>

		<label>
			Display name
			<input
				name="displayName"
				required
				maxlength={LIMITS.displayName}
				placeholder="Ada Lovelace"
				value={form?.values?.displayName ?? ''}
			/>
			{#if form?.errors?.displayName}<small class="error">{form.errors.displayName}</small>{/if}
		</label>

		<button class="button" type="submit">Create my page</button>
	</form>
</main>
