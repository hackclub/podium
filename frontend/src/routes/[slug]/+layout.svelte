<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { eventToTheme, type EventTheme } from '$lib/theme';
	import { getEventBySlug, getEvent, type ApiEvent } from '$lib/api';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { fade } from 'svelte/transition';
	import { onDestroy } from 'svelte';
	import { setContext } from 'svelte';
	import { writable } from 'svelte/store';

	const { children } = $props();

	const slug = $derived(page.params.slug ?? '');

	// Shared state accessible by child pages via getContext
	const eventStore = writable<ApiEvent | null>(null);
	const eventThemeStore = writable<EventTheme | null>(null);
	const eventIdStore = writable<string | null>(null);
	setContext('event', eventStore);
	setContext('eventTheme', eventThemeStore);
	setContext('eventId', eventIdStore);

	let eventData: ApiEvent | null = $state(null);
	let eventTheme: EventTheme | null = $state(null);
	let loading = $state(true);
	let eventSource: EventSource | null = null;

	function deriveStage(e: { enabled: boolean; votable: boolean; voting_closed: boolean; leaderboard_enabled: boolean }) {
		if (e.leaderboard_enabled && e.voting_closed) return 'results';
		if (e.voting_closed) return 'closed';
		if (e.votable) return 'voting';
		if (e.enabled) return 'live';
		return 'draft';
	}

	function redirectForStage(stage: string, currentSlug: string) {
		const currentPath = page.url.pathname;
		switch (stage) {
			case 'draft':
				// Event disabled — go to landing
				goto(`/${currentSlug}`);
				break;
			case 'live':
				// Submissions open — if on vote page, go to create
				if (currentPath.includes('/vote')) {
					goto(`/${currentSlug}/create`);
				}
				// Team editing only available after submissions close
				if (currentPath.includes('/team')) {
					goto(`/${currentSlug}/create`);
				}
				break;
			case 'voting':
			case 'closed':
				// Voting or closed — if on create page, go to vote
				if (currentPath.includes('/create')) {
					goto(`/${currentSlug}/vote`);
				}
				break;
			case 'results':
				// Results — go to vote page (which shows leaderboard)
				if (currentPath.includes('/create')) {
					goto(`/${currentSlug}/vote`);
				}
				break;
		}
	}

	function connectSSE(eventId: string, currentSlug: string) {
		eventSource?.close();
		const url = `${PUBLIC_API_URL || '/api'}/events/${eventId}/stage-stream`;
		const es = new EventSource(url);
		es.onmessage = (msg) => {
			try {
				const flags = JSON.parse(msg.data);
				if (eventData) {
					const updated = { ...eventData, ...flags };
					eventData = updated;
					eventTheme = eventToTheme(updated);
					eventStore.set(updated);
					eventThemeStore.set(eventTheme);

					const stage = deriveStage(flags);
					redirectForStage(stage, currentSlug);
				}
			} catch { /* ignore malformed messages */ }
		};
		eventSource = es;
	}

	async function loadEvent(s: string) {
		loading = true;
		try {
			const id = await getEventBySlug(s);
			const event = await getEvent(id);
			eventData = event;
			eventTheme = eventToTheme(event);
			eventStore.set(event);
			eventThemeStore.set(eventTheme);
			eventIdStore.set(id);
			connectSSE(id, s);
		} catch {
			eventData = null;
			eventTheme = null;
		} finally {
			loading = false;
		}
	}

	onDestroy(() => {
		eventSource?.close();
	});

	let lastLoadedSlug = '';
	$effect(() => {
		if (slug && slug !== lastLoadedSlug) {
			lastLoadedSlug = slug;
			loadEvent(slug);
		}
	});
</script>

{#key slug}
	{#if loading}
		<div class="flex min-h-screen items-center justify-center bg-[#111]">
			<p class="text-white/60">Loading...</p>
		</div>
	{:else if eventTheme && eventData}
		<div
			class="flex min-h-screen flex-col bg-cover bg-center"
			style="background-image: url({eventTheme.background});"
			in:fade={{ duration: 200 }}
		>
			<header class="flex flex-col items-center gap-6 px-20 pt-6">
				<div class="flex flex-col items-center justify-center">
					<eventTheme.logo satellite={eventData.name.replace(/^campfire\s*/i, '')} height={64} />
				</div>
			</header>

			{#if !eventData.enabled}
				<main class="flex flex-1 items-center justify-center px-4">
					<div
						class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-10 drop-shadow-md text-center"
						style="font-family: {eventTheme.font};"
					>
						<div
							class="absolute inset-0"
							style="background-color: {eventTheme.primary};"
						></div>
						<div class="relative flex flex-col items-center gap-3">
							<p class="text-3xl text-white drop-shadow-md">This event is not available yet</p>
							<p class="text-lg text-white/70 drop-shadow-md">Check back later!</p>
						</div>
					</div>
				</main>
			{:else}
				{@render children()}
			{/if}
		</div>
	{:else}
		<div class="flex min-h-screen items-center justify-center bg-[#111]">
			<p class="text-white/60">Event not found</p>
		</div>
	{/if}
{/key}
