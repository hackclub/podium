<script lang="ts">
	import { page } from '$app/state';
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';

	const { children } = $props();

	const slug = $derived(page.params.slug);
	const eventData = $derived(events[slug]);
	const eventTheme = $derived(eventData ? theme[eventData.theme] : null);
</script>

<div
	class="flex min-h-screen flex-col bg-cover bg-center"
	style="background-image: url({eventTheme?.background});"
>
	<header class="flex flex-col items-center gap-6 px-20 pt-6">
		<div class="flex flex-col items-center justify-center">
			{#if eventTheme}
				<eventTheme.logo satellite={eventData?.satellite ?? ''} height={64} />
			{/if}
		</div>
	</header>

	{@render children()}
</div>
