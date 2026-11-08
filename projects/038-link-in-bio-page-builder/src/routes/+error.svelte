<script>
	import { page } from '$app/state';
</script>

<svelte:head><title>{page.status} · Linkpage</title></svelte:head>

<main class="center">
	<h1>{page.status === 404 ? 'Page not found' : 'Something went wrong'}</h1>
	<p class="muted">{page.status === 404 ? 'This link may have been mistyped.' : 'Please try again.'}</p>
	<a class="button" href="/">Build a page</a>
</main>
