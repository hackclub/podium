<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { EventTheme } from '$lib/theme';
	import { getProject, vote as submitVote, type ApiProject, type ApiEvent } from '$lib/api';
	import { isLoggedIn } from '$lib/auth';
	import Button from '$lib/forms/Button.svelte';
	import ProfileGate from '$lib/forms/ProfileGate.svelte';

	const eventThemeStore = getContext<Writable<EventTheme | null>>('eventTheme');
	const eventIdStore = getContext<Writable<string | null>>('eventId');
	const eventStore = getContext<Writable<ApiEvent | null>>('event');

	let eventTheme: EventTheme | null = $state(null);
	let eventId: string | null = $state(null);
	let eventData: ApiEvent | null = $state(null);

	$effect(() => {
		const unsub1 = eventThemeStore.subscribe((v) => (eventTheme = v));
		const unsub2 = eventIdStore.subscribe((v) => (eventId = v));
		const unsub3 = eventStore.subscribe((v) => (eventData = v));
		return () => { unsub1(); unsub2(); unsub3(); };
	});

	const slug = $derived(page.params.slug);
	const id = $derived(page.params.id ?? '');

	const isFlagship = $derived((eventData as ApiEvent | null)?.feature_flags_csv?.includes('flagship') ?? false);

	let project: (ApiProject & { join_code: string; hours_spent: number; event_id: string }) | null = $state(null);
	let loading = $state(true);
	let loadError = $state('');
	let voteStatus = $state<'idle' | 'voting' | 'voted' | 'error'>('idle');
	let voteError = $state('');

	onMount(async () => {
		try {
			project = await getProject(id);
		} catch (e: any) {
			project = null;
			loadError = e.message || 'Project not found';
		} finally {
			loading = false;
		}
	});

	async function handleVote() {
		if (!eventId || !project || !isLoggedIn()) return;
		voteStatus = 'voting';
		try {
			await submitVote(eventId, [project.id]);
			voteStatus = 'voted';
		} catch (e: any) {
			voteStatus = 'error';
			voteError = e.message || 'Failed to vote';
		}
	}
</script>

{#if eventTheme}
<ProfileGate {eventTheme}>
<main class="flex flex-1 items-center justify-center px-4 py-12">
	{#if loading}
		<p class="text-white/60">Loading...</p>
	{:else if eventTheme && project}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0"
				style="background-color: {eventTheme.primary};"
			></div>

			<div class="relative flex flex-col gap-2">
				<button
					type="button"
					class="mt-1 mb-2 w-fit text-md text-white/70 underline drop-shadow-md cursor-pointer transition-colors ease-in-out duration-125 hover:text-[var(--hover-color)]"
					style="--hover-color: {eventTheme.selected};"
					onclick={() => goto(`/${slug}/vote`)}
				>
					back
				</button>

				<div class="h-40 w-full overflow-hidden rounded-xl bg-gray-300">
					{#if project.image_url}
						<img
							src={project.image_url}
							alt={project.name}
							class="h-full w-full object-cover"
						/>
					{/if}
				</div>

				<div class="flex flex-col text-white drop-shadow-md">
					<p class="text-4xl">{project.name}</p>
					<p class="text-xl text-white/80">{project.description}</p>
				</div>

				<div class="flex flex-col gap-1 drop-shadow-md">
					{#if project.owner_name}
						<p class="text-sm text-white/50">
							<span class="text-white/30">Submitted by</span>
							<span class="text-white/70">{project.owner_name}</span>
						</p>
					{/if}

					{#if project.collaborators?.length > 0}
						<p class="text-sm text-white/50">
							<span class="text-white/30">Teammates:</span>
							{#each project.collaborators as collab, ci}
								<span class="text-white/70">{collab.display_name}</span>{#if ci < project.collaborators.length - 1}<span class="text-white/30">,</span>{/if}
							{/each}
						</p>
					{/if}
				</div>

				{#if voteStatus === 'voted'}
					<p class="text-lg text-green-300 drop-shadow-md">Vote submitted!</p>
				{/if}
				{#if voteStatus === 'error'}
					<p class="text-sm text-red-300 drop-shadow-md">{voteError}</p>
				{/if}

				<div class="flex gap-2.5 flex-col md:flex-row">
					{#if project.demo}
						<a href={project.demo} target="_blank" rel="noopener noreferrer" class="flex-1">
							<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full">Demo</Button>
						</a>
					{/if}
					{#if project.repo}
						<a href={project.repo} target="_blank" rel="noopener noreferrer" class="flex-1">
							<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full">Repository</Button>
						</a>
					{/if}
					{#if isFlagship}
						<!-- No voting for flagship events -->
					{:else if eventData !== null && eventData.voting_closed}
						<div class="flex-1">
							<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full" disabled>
								Voting is closed
							</Button>
						</div>
					{:else if eventData !== null && !eventData.votable}
						<div class="flex-1">
							<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full" disabled>
								Voting not open
							</Button>
						</div>
					{:else}
						<div class="flex-1">
							<Button
								color={eventTheme.primary}
								selectedColor={eventTheme.selected}
								class="w-full"
								onclick={handleVote}
								disabled={voteStatus === 'voting' || voteStatus === 'voted' || !isLoggedIn() || eventData === null}
							>
								{voteStatus === 'voting' ? 'Voting...' : voteStatus === 'voted' ? 'Voted!' : 'Vote'}
							</Button>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{:else}
		<div class="flex flex-col items-center gap-4">
			<p class="text-white/60">{loadError || 'Project not found'}</p>
			<button
				type="button"
				class="text-md text-white/70 underline cursor-pointer hover:text-white/90"
				onclick={() => goto(`/${slug}/vote`)}
			>
				back to projects
			</button>
		</div>
	{/if}
</main>
</ProfileGate>
{/if}
