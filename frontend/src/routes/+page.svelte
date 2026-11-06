<script lang="ts">
	import { buildTheme, skinStyle } from '$lib/theme';
	import { getOfficialEvents, type ApiEvent } from '$lib/api';
	import { fade } from 'svelte/transition';
	import { onMount } from 'svelte';

	// The event picker wears the Haven theme; each card links to its own event page.
	const theme = buildTheme('haven');

	let searchQuery = $state('');
	let events: ApiEvent[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	/** "Haven Ankara" → "Ankara"; other events keep their full name. */
	function shortName(event: ApiEvent) {
		return event.feature_flags_csv?.includes('haven') ? event.name.replace(/^haven\s*/i, '') : event.name;
	}

	/** Haven descriptions are "<length> game jam in <city>"; the card already shows the city. */
	function subtitle(event: ApiEvent) {
		return event.feature_flags_csv?.includes('haven') ? event.description.replace(/\s+in\s.*$/i, '') : event.description;
	}

	let filteredEvents = $derived(
		events
			.filter((e) => e.name.toLowerCase().includes(searchQuery.toLowerCase()))
			.sort((a, b) => shortName(a).localeCompare(shortName(b)))
	);

	onMount(async () => {
		try {
			events = await getOfficialEvents();
		} catch (e: any) {
			error = e.message || 'Failed to load events';
		} finally {
			loading = false;
		}
	});
</script>

<div
	class="min-h-screen"
	style="font-family: {theme.font}; --accent: {theme.selected}; {skinStyle(theme.skin)}"
	out:fade={{ duration: 150 }}
>
	<!-- A fixed layer instead of background-attachment: fixed, which makes Safari repaint on every scroll. -->
	<div class="fixed inset-0 -z-10 bg-cover bg-center" style="background-image: url({theme.background});"></div>

	<header class="flex flex-col items-center gap-3 px-4 pt-10 text-center">
		<img src="/haven-logo.webp" alt="Hack Club Haven" class="h-28 w-auto object-contain sm:h-36" />
		<h1
			class="font-(family-name:--heading-font) text-4xl leading-none text-white sm:text-6xl"
			style="text-shadow: 0 0 10px #ffd059, 0 0 4px #ed5615;"
		>
			Vote for your favorite games
		</h1>
		<p class="text-lg text-white drop-shadow-md">Find your city to submit your game and vote</p>
	</header>

	<main class="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-10">
		<label
			class="mx-auto flex w-full max-w-xl items-center gap-2 rounded-full border-4 border-(--line) bg-(--field) px-5 py-3 shadow-md transition-colors focus-within:border-(--accent)"
		>
			<span class="sr-only">Search for your city</span>
			<input
				type="text"
				placeholder="Search for your city"
				bind:value={searchQuery}
				class="min-w-0 flex-1 bg-transparent text-lg text-(--ink) placeholder:text-(--ink)/50 outline-none"
			/>
			<svg viewBox="0 0 24 24" class="size-6 shrink-0 text-(--ink)" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
				<circle cx="11" cy="11" r="7" />
				<path d="m20 20-3.5-3.5" />
			</svg>
		</label>

		{#if loading}
			<p class="py-8 text-center text-lg text-white drop-shadow-md">Loading events...</p>
		{:else if error}
			<p class="mx-auto rounded-2xl bg-(--surface) px-5 py-3 text-center text-(--danger)">{error}</p>
		{:else if filteredEvents.length === 0}
			<p class="py-8 text-center text-lg text-white drop-shadow-md">No events found</p>
		{:else}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each filteredEvents as event, i (event.id)}
					<a
						href="/{event.slug}"
						in:fade|global={{ duration: 100, delay: Math.min(i, 20) * 15 }}
						class="group flex items-center justify-between gap-3 rounded-2xl border-4 border-(--edge) bg-(--surface) p-4 shadow-md transition-transform duration-200 hover:-translate-y-1 focus-visible:-translate-y-1"
					>
						<div class="flex min-w-0 flex-col">
							<span class="font-(family-name:--heading-font) text-2xl leading-tight text-(--ink) wrap-anywhere">
								{shortName(event)}
							</span>
							{#if event.description}
								<span class="text-sm text-(--ink)/60 wrap-anywhere">{subtitle(event)}</span>
							{/if}
						</div>
						<span
							class="shrink-0 rounded-full bg-(--button) px-3 py-1.5 text-sm text-(--button-ink) transition-colors group-hover:bg-(--accent) group-hover:text-(--button-hover-ink)"
						>
							Vote →
						</span>
					</a>
				{/each}
			</div>
		{/if}
	</main>

	<footer class="flex items-center justify-center gap-6 pb-8 text-white drop-shadow-md">
		<a href="https://hack-club-hq.gitbook.io/campfire/campfire" target="_blank" rel="noopener noreferrer" class="underline hover:text-(--accent)">Podium Guide</a>
		<a href="/admin/login" class="underline hover:text-(--accent)">POC Login</a>
	</footer>
</div>
