<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { adminGetLeaderboard, adminGetEvent, adminSetProjectPoints, type ApiLeaderboardProject, type ApiAdminEvent } from '$lib/api';

	const eventId = $derived(page.params.id ?? '');

	let event: ApiAdminEvent | null = $state(null);
	let projects: ApiLeaderboardProject[] = $state([]);
	let expandedId: string | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let savingId: string | null = $state(null);

	const isFlagship = $derived((event as ApiAdminEvent | null)?.feature_flags_csv?.includes('flagship') ?? false);

	onMount(async () => {
		try {
			const [ev, lb] = await Promise.all([
				adminGetEvent(eventId),
				adminGetLeaderboard(eventId),
			]);
			event = ev;
			projects = lb;
		} catch (e: any) {
			error = e.message || 'Failed to load leaderboard';
		} finally {
			loading = false;
		}
	});

	async function savePoints(projectId: string, points: number) {
		savingId = projectId;
		try {
			await adminSetProjectPoints(eventId, projectId, points);
			// Re-sort after save
			projects = [...projects].sort((a, b) => b.manual_points - a.manual_points);
		} catch (e: any) {
			error = e.message || 'Failed to save points';
		} finally {
			savingId = null;
		}
	}
</script>

<div class="max-w-4xl">
	<div class="flex items-center gap-3 mb-8">
		<button
			type="button"
			onclick={() => goto(`/admin/events/${eventId}`)}
			class="text-white/40 hover:text-white transition-colors"
		>
			← Back
		</button>
		<h1 class="text-3xl font-bold text-white">Leaderboard</h1>
		{#if isFlagship}
			<span class="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">Flagship</span>
		{/if}
	</div>

	{#if loading}
		<p class="text-white/60">Loading...</p>
	{:else if error}
		<p class="text-red-400">{error}</p>
	{:else if projects.length === 0}
		<p class="text-white/60 text-center py-12">No projects yet</p>
	{:else}
		<div class="flex flex-col gap-2">
			{#each projects as project, i}
				{@const isExpanded = expandedId === project.id}
				<div class="rounded-lg bg-white/5 border border-white/10 overflow-hidden">
					<button
						type="button"
						class="flex items-center justify-between w-full p-4 text-left hover:bg-white/5 transition-colors"
						onclick={() => expandedId = isExpanded ? null : project.id}
					>
						<div class="flex items-center gap-4 min-w-0">
							<span class="text-2xl font-bold w-10 text-right shrink-0 {i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-600' : 'text-white/30'}">
								#{i + 1}
							</span>
							{#if project.image_url}
								<img src={project.image_url} alt="" class="w-12 h-12 rounded object-cover shrink-0" />
							{:else}
								<div class="w-12 h-12 rounded bg-white/10 shrink-0"></div>
							{/if}
							<div class="min-w-0">
								<p class="text-white font-medium">{project.name}</p>
								<p class="text-white/40 text-xs truncate max-w-md">{project.description}</p>
							</div>
						</div>
						<div class="flex items-center gap-4 shrink-0">
							{#if isFlagship}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div class="flex items-center gap-2" onclick={(e) => e.stopPropagation()}>
									<input
										type="number"
										min="0"
										value={project.manual_points}
										onchange={(e) => {
											const val = parseInt(e.currentTarget.value) || 0;
											project.manual_points = val;
											savePoints(project.id, val);
										}}
										disabled={savingId === project.id}
										class="w-20 px-2 py-1 text-right text-white bg-white/10 border border-white/20 rounded text-lg font-bold focus:outline-none focus:border-blue-400 disabled:opacity-50"
									/>
									<span class="text-white/40 text-sm">pts</span>
								</div>
							{:else}
								<div class="flex items-center gap-2">
									<span class="text-2xl font-bold text-white">{project.points}</span>
									<span class="text-white/40 text-sm">votes</span>
								</div>
							{/if}
							<span class="text-white/30 text-sm transition-transform {isExpanded ? 'rotate-180' : ''}">▼</span>
						</div>
					</button>

					{#if isExpanded}
						<div class="px-4 pb-4 pt-0 ml-14 border-t border-white/5 mt-0 pt-3 flex flex-col gap-3">
							{#if project.image_url}
								<img src={project.image_url} alt={project.name} class="w-full max-w-md rounded-lg object-cover" />
							{/if}

							<p class="text-white/60 text-sm">{project.description}</p>

							<div class="flex flex-col gap-1.5">
								{#if project.owner_name}
									<div class="text-sm text-white/50">
										<span class="text-white/30">Submitted by</span>
										<span class="text-white/70">{project.owner_name}</span>
									</div>
								{/if}

								{#if project.collaborators?.length > 0}
									<div class="text-sm text-white/50">
										<span class="text-white/30">Teammates:</span>
										{#each project.collaborators as collab, ci}
											<span class="text-white/70">{collab.display_name}</span>{#if ci < project.collaborators.length - 1}<span class="text-white/30">,</span>{/if}
										{/each}
									</div>
								{/if}

								{#if project.hours_spent}
									<div class="text-sm text-white/50">
										<span class="text-white/30">Hours spent:</span>
										<span class="text-white/70">{project.hours_spent}</span>
									</div>
								{/if}
							</div>

							{#if project.repo || project.demo}
								<div class="flex gap-3 flex-wrap">
									{#if project.repo}
										<a href={project.repo} target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 text-sm">
											Repo ↗
										</a>
									{/if}
									{#if project.demo}
										<a href={project.demo} target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 text-sm">
											Demo ↗
										</a>
									{/if}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
