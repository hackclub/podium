<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { EventTheme } from '$lib/theme';
	import { getEventProjects, getMyVotes, vote as submitVote, attendEvent, type ApiProject, type ApiEvent } from '$lib/api';
	import { isLoggedIn } from '$lib/auth';
	import ProfileGate from '$lib/forms/ProfileGate.svelte';
	import Button from '$lib/forms/Button.svelte';

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
	let projects: ApiProject[] = $state([]);
	let loading = $state(true);
	let hoveredId: string | null = $state(null);
	let expandedId: string | null = $state(null);
	const showLeaderboard = $derived((eventData as ApiEvent | null)?.leaderboard_enabled ?? false);
	const isFlagship = $derived((eventData as ApiEvent | null)?.feature_flags_csv?.includes('flagship') ?? false);

	// Multi-vote state
	let selectedIds = $state(new Set<string>());
	let votedIds = $state(new Set<string>());
	let submitting = $state(false);
	let submitError = $state('');

	const maxVotes = $derived((eventData as ApiEvent | null)?.max_votes_per_user ?? 3);
	const remainingVotes = $derived(maxVotes - votedIds.size);
	const canSelectMore = $derived(selectedIds.size < remainingVotes);

	function toggleProject(projectId: string) {
		if (votedIds.has(projectId)) return;
		const next = new Set(selectedIds);
		if (next.has(projectId)) {
			next.delete(projectId);
		} else if (canSelectMore) {
			next.add(projectId);
		}
		selectedIds = next;
	}

	async function handleSubmit() {
		if (!eventId || selectedIds.size === 0 || submitting) return;
		submitting = true;
		submitError = '';
		try {
			await submitVote(eventId, [...selectedIds]);
			const next = new Set(votedIds);
			for (const id of selectedIds) next.add(id);
			votedIds = next;
			selectedIds = new Set();
		} catch (e: any) {
			submitError = e.message || 'Failed to submit votes';
		} finally {
			submitting = false;
		}
	}

	$effect(() => {
		if (eventId && eventData) {
			loading = true;
			const promises: Promise<any>[] = [
				getEventProjects(eventId, eventData.leaderboard_enabled).then((p) => {
					projects = p;
				}),
			];
			if (isLoggedIn()) {
				promises.push(
					attendEvent(eventId).catch(() => {}),
					getMyVotes(eventId).then((ids) => {
						votedIds = new Set(ids);
					}).catch(() => {}),
				);
			}
			Promise.all(promises).finally(() => {
				loading = false;
			});
		}
	});
</script>

{#if eventTheme}
<ProfileGate {eventTheme}>
<main class="flex flex-1 items-center justify-center px-4 py-12">
	{#if showLeaderboard}
			<div
				class="relative w-full max-w-2xl overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
				style="font-family: {eventTheme.font};"
			>
				<div
					class="absolute inset-0"
					style="background-color: {eventTheme.primary};"
				></div>
				<div class="relative flex flex-col gap-4">
					<p class="text-2xl text-white drop-shadow-md text-center">Leaderboard</p>

					{#if loading}
						<p class="text-white/60 text-center py-8">Loading results...</p>
					{:else if projects.length === 0}
						<p class="text-white/60 text-center py-8">No projects yet</p>
					{:else}
						<div class="flex flex-col gap-2">
							{#each projects as project, i}
								{@const isExpanded = expandedId === project.id}
								<div class="rounded-xl border-2 overflow-hidden transition-all" style="background-color: {eventTheme.primary}; border-color: {hoveredId === project.id || isExpanded ? eventTheme.selected : 'rgba(255,255,255,0.2)'};">
									<button
										type="button"
										class="flex items-center justify-between w-full p-3 text-left transition-all hover:scale-[1.005] cursor-pointer"
										onmouseenter={() => (hoveredId = project.id)}
										onmouseleave={() => (hoveredId = null)}
										onclick={() => expandedId = isExpanded ? null : project.id}
									>
										<div class="flex items-center gap-3">
											<span class="text-2xl font-bold w-10 text-right drop-shadow-md {i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-600' : 'text-white/30'}">
												#{i + 1}
											</span>
											{#if project.image_url}
												<img src={project.image_url} alt="" class="w-12 h-12 rounded object-cover" />
											{:else}
												<div class="w-12 h-12 rounded bg-white/10"></div>
											{/if}
											<div class="text-left">
												<p class="text-white font-medium drop-shadow-md">{project.name}</p>
												<p class="text-white/50 text-xs truncate max-w-xs drop-shadow-md">{project.description}</p>
											</div>
										</div>
										<div class="flex items-center gap-3">
											<div class="flex items-center gap-1.5">
												<span class="text-2xl font-bold text-white drop-shadow-md">{project.points}</span>
												<span class="text-white/40 text-sm drop-shadow-md">{isFlagship ? 'pts' : 'votes'}</span>
											</div>
											<span class="text-white/30 text-sm transition-transform drop-shadow-md {isExpanded ? 'rotate-180' : ''}">▼</span>
										</div>
									</button>

									{#if isExpanded}
										<div class="px-4 pb-4 pt-0 ml-13 border-t border-white/10 mt-0 pt-3 flex flex-col gap-2">
											<p class="text-white/70 text-sm drop-shadow-md">{project.description}</p>

											{#if project.repo || project.demo}
												<div class="flex gap-3 flex-wrap">
													{#if project.demo}
														<a href={project.demo} target="_blank" rel="noopener" class="text-sm font-medium drop-shadow-md hover:opacity-80 transition-opacity" style="color: {eventTheme.selected};">
															Demo ↗
														</a>
													{/if}
													{#if project.repo}
														<a href={project.repo} target="_blank" rel="noopener" class="text-sm font-medium drop-shadow-md hover:opacity-80 transition-opacity" style="color: {eventTheme.selected};">
															Repo ↗
														</a>
													{/if}
												</div>
											{/if}

											{#if project.owner_name || project.owner_email}
												<div class="text-sm text-white/50 drop-shadow-md">
													<span class="text-white/30">Submitted by</span>
													<span class="text-white/70">{project.owner_name || project.owner_email}</span>
												</div>
											{/if}

											{#if project.collaborators?.length > 0}
												<div class="text-sm text-white/50 drop-shadow-md">
													<span class="text-white/30">Teammates:</span>
													{#each project.collaborators as collab, ci}
														<span class="text-white/70">{collab.display_name || collab.email}</span>{#if ci < project.collaborators.length - 1}<span class="text-white/30">,</span>{/if}
													{/each}
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		{:else if isFlagship}
			<div
				class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-10 drop-shadow-md text-center"
				style="font-family: {eventTheme.font};"
			>
				<div
					class="absolute inset-0"
					style="background-color: {eventTheme.primary};"
				></div>
				<div class="relative flex flex-col items-center gap-3">
					<p class="text-3xl text-white drop-shadow-md">Thanks for submitting your project!</p>
					<p class="text-lg text-white/70 drop-shadow-md">Results will be announced soon.</p>
				</div>
			</div>
		{:else if eventData && eventData.voting_closed}
			<div
				class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-10 drop-shadow-md text-center"
				style="font-family: {eventTheme.font};"
			>
				<div
					class="absolute inset-0"
					style="background-color: {eventTheme.primary};"
				></div>
				<div class="relative flex flex-col items-center gap-3">
					<p class="text-3xl text-white drop-shadow-md">Voting is closed</p>
					<p class="text-lg text-white/70 drop-shadow-md">Results will be shown soon.</p>
				</div>
			</div>
		{:else if eventData && !eventData.votable}
			<div
				class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-10 drop-shadow-md text-center"
				style="font-family: {eventTheme.font};"
			>
				<div
					class="absolute inset-0"
					style="background-color: {eventTheme.primary};"
				></div>
				<div class="relative flex flex-col items-center gap-3">
					<p class="text-3xl text-white drop-shadow-md">Thanks for submitting your project!</p>
					<p class="text-lg text-white/70 drop-shadow-md">Voting will open soon.</p>
				</div>
			</div>
		{:else}
			<div
				class="relative overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
				style="font-family: {eventTheme.font};"
			>
				<div
					class="absolute inset-0"
					style="background-color: {eventTheme.primary};"
				></div>

				<div class="relative flex flex-col gap-4">
					<div class="flex flex-col gap-1">
						<p class="text-2xl text-white drop-shadow-md">Vote for your favorites</p>
						{#if !loading}
							<div class="flex items-center gap-2">
								{#each Array(maxVotes) as _, i}
									<div
										class="w-3 h-3 rounded-full transition-colors duration-200"
										style="background-color: {i < votedIds.size + selectedIds.size ? eventTheme.selected : 'rgba(255,255,255,0.3)'};"
									></div>
								{/each}
								<p class="text-sm text-white/70 drop-shadow-md ml-1">
									{#if remainingVotes <= 0}
										All votes used!
									{:else}
										{remainingVotes} vote{remainingVotes === 1 ? '' : 's'} remaining
									{/if}
								</p>
							</div>
						{/if}
					</div>

					{#if loading}
						<p class="text-white/60 text-center py-8">Loading projects...</p>
					{:else if projects.length === 0}
						<p class="text-white/60 text-center py-8">No projects yet</p>
					{:else}
						<div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
							{#each projects as project}
								{@const isVoted = votedIds.has(project.id)}
								{@const isSelected = selectedIds.has(project.id)}
								{@const isActive = isVoted || isSelected}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									role="button"
									tabindex="0"
									class="relative flex w-[280px] cursor-pointer flex-col gap-2.5 overflow-hidden rounded-xl border-4 p-3 text-left shadow-md transition-all hover:scale-[1.02]"
									style="background-color: {eventTheme.primary}; border-color: {isActive ? eventTheme.selected : hoveredId === project.id ? eventTheme.selected : 'white'}; color: {isActive || hoveredId === project.id ? eventTheme.selected : 'white'}; opacity: {!isVoted && !isSelected && !canSelectMore ? '0.5' : '1'};"
									onmouseenter={() => (hoveredId = project.id)}
									onmouseleave={() => (hoveredId = null)}
									onclick={() => toggleProject(project.id)}
									onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleProject(project.id); } }}
								>
									{#if isVoted}
										<div
											class="absolute top-2 right-2 z-10 flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold text-white drop-shadow-md"
											style="background-color: {eventTheme.selected};"
										>
											Voted
										</div>
									{:else if isSelected}
										<div
											class="absolute top-2 right-2 z-10 flex h-6 w-6 items-center justify-center rounded-full text-white drop-shadow-md"
											style="background-color: {eventTheme.selected};"
										>
											&#10003;
										</div>
									{/if}

									<div class="h-[100px] w-full rounded bg-gray-300">
										{#if project.image_url}
											<img
												src={project.image_url}
												alt={project.name}
												class="h-full w-full rounded object-cover"
											/>
										{/if}
									</div>

									<div class="flex flex-col gap-0.5 drop-shadow-md">
										<p class="text-2xl">{project.name}</p>
										<p class="text-sm opacity-80">{project.description}</p>
									</div>

									<div class="flex w-full items-center justify-between">
										<span class="text-xs">
											{#if isVoted}
												Already voted
											{:else if isSelected}
												Selected
											{:else}
												Tap to select
											{/if}
										</span>
										<a
											href="/{slug}/vote/{project.id}"
											class="rounded-lg border-2 border-white/40 px-3 py-1.5 text-sm font-medium text-white hover:border-white hover:bg-white/10 transition-all"
											onclick={(e) => e.stopPropagation()}
										>
											View details
										</a>
									</div>
								</div>
							{/each}
						</div>

						{#if submitError}
							<p class="text-sm text-red-300 drop-shadow-md text-center">{submitError}</p>
						{/if}

						{#if remainingVotes > 0}
							<div class="sticky bottom-4 mt-2">
								<Button
									color={eventTheme.primary}
									selectedColor={eventTheme.selected}
									class="w-full"
									onclick={handleSubmit}
									disabled={selectedIds.size === 0 || submitting || !isLoggedIn()}
								>
									{#if submitting}
										Submitting...
									{:else if selectedIds.size === 0}
										Select projects to vote
									{:else}
										Submit {selectedIds.size} vote{selectedIds.size === 1 ? '' : 's'}
									{/if}
								</Button>
							</div>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
</main>
</ProfileGate>
{/if}
