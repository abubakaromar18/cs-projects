<script>
	import ProfileCard from '#lib/components/ProfileCard.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.profile.displayName}</title>
	{#if data.profile.bio}<meta name="description" content={data.profile.bio} />{/if}
</svelte:head>

<ProfileCard {...data.profile} />
