<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { adminGetEventStats, type ApiEventStats } from '$lib/api';

	const eventId = $derived(page.params.id ?? '');

	let stats: ApiEventStats | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let tab: 'submissions' | 'leaderboard' = $state('submissions');
	let filter: 'all' | 'submitted' | 'missing' = $state('all');
	let searchQuery = $state('');

	let filteredAttendees = $derived(() => {
		if (!stats) return [];
		let list = stats.attendees;
		if (filter === 'submitted') list = list.filter((a) => a.has_project);
		if (filter === 'missing') list = list.filter((a) => !a.has_project);
		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			list = list.filter((a) =>
				`${a.first_name} ${a.last_name} ${a.email} ${a.display_name}`
					.toLowerCase()
					.includes(q)
			);
		}
		return list;
	});

	onMount(async () => {
		try {
			stats = await adminGetEventStats(eventId);
		} catch (e: any) {
			error = e.message || 'Failed to load stats';
		} finally {
			loading = false;
		}
	});
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
		<h1 class="text-3xl font-bold text-white">Event Stats</h1>
	</div>

	{#if loading}
		<p class="text-white/60">Loading...</p>
	{:else if error}
		<p class="text-red-400">{error}</p>
	{:else if stats}
		<!-- Summary Cards -->
		<div class="grid grid-cols-3 gap-4 mb-8">
			<div class="p-4 rounded-lg bg-white/5 border border-white/10">
				<p class="text-3xl font-bold text-white">{stats.total_attendees}</p>
				<p class="text-white/40 text-sm">Total Attendees</p>
			</div>
			<div class="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
				<p class="text-3xl font-bold text-emerald-400">{stats.submitted_count}</p>
				<p class="text-white/40 text-sm">Submitted Projects</p>
			</div>
			<div class="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
				<p class="text-3xl font-bold text-amber-400">{stats.missing_count}</p>
				<p class="text-white/40 text-sm">Missing Projects</p>
			</div>
		</div>

		<!-- Progress Bar -->
		{#if stats.total_attendees > 0}
			<div class="mb-8">
				<div class="flex justify-between text-sm text-white/60 mb-2">
					<span>Submission Progress</span>
					<span>{Math.round((stats.submitted_count / stats.total_attendees) * 100)}%</span>
				</div>
				<div class="w-full h-3 rounded-full bg-white/10 overflow-hidden">
					<div
						class="h-full rounded-full bg-emerald-500 transition-all"
						style="width: {(stats.submitted_count / stats.total_attendees) * 100}%"
					></div>
				</div>
			</div>
		{/if}

		<!-- Tabs -->
		<div class="flex gap-1 mb-6 bg-white/5 rounded-lg p-1 border border-white/10">
			<button
				type="button"
				onclick={() => (tab = 'submissions')}
				class="flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors {tab === 'submissions' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'}"
			>
				Submissions ({stats.total_attendees})
			</button>
			<button
				type="button"
				onclick={() => (tab = 'leaderboard')}
				class="flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors {tab === 'leaderboard' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'}"
			>
				Vote Leaderboard ({stats.leaderboard.length})
			</button>
		</div>

		{#if tab === 'submissions'}
			<!-- Filter & Search -->
			<div class="flex gap-2 mb-4">
				<div class="flex gap-1 bg-white/5 rounded-md p-1 border border-white/10">
					<button
						type="button"
						onclick={() => (filter = 'all')}
						class="px-3 py-1 rounded text-xs transition-colors {filter === 'all' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'}"
					>
						All
					</button>
					<button
						type="button"
						onclick={() => (filter = 'submitted')}
						class="px-3 py-1 rounded text-xs transition-colors {filter === 'submitted' ? 'bg-emerald-500/20 text-emerald-400' : 'text-white/40 hover:text-white/60'}"
					>
						Submitted
					</button>
					<button
						type="button"
						onclick={() => (filter = 'missing')}
						class="px-3 py-1 rounded text-xs transition-colors {filter === 'missing' ? 'bg-amber-500/20 text-amber-400' : 'text-white/40 hover:text-white/60'}"
					>
						Missing
					</button>
				</div>
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Search attendees..."
					class="flex-1 px-3 py-1.5 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm placeholder:text-white/30"
				/>
			</div>

			{@const list = filteredAttendees()}
			{#if list.length === 0}
				<p class="text-white/60 text-center py-12">No attendees found</p>
			{:else}
				<div class="flex flex-col gap-2">
					{#each list as attendee}
						<div class="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
							<div>
								<p class="text-white text-sm">
									{attendee.first_name} {attendee.last_name}
									{#if attendee.display_name}
										<span class="text-white/40">({attendee.display_name})</span>
									{/if}
								</p>
								<p class="text-white/40 text-xs">{attendee.email}</p>
							</div>
							{#if attendee.has_project}
								<span class="px-2.5 py-1 rounded-full text-xs bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
									Submitted
								</span>
							{:else}
								<span class="px-2.5 py-1 rounded-full text-xs bg-amber-500/15 text-amber-400 border border-amber-500/20">
									Missing
								</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{:else}
			<!-- Leaderboard -->
			{#if stats.leaderboard.length === 0}
				<p class="text-white/60 text-center py-12">No projects yet</p>
			{:else}
				<div class="flex flex-col gap-2">
					{#each stats.leaderboard as project, i}
						<div class="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10">
							<div class="flex items-center gap-4">
								<span class="text-2xl font-bold w-10 text-right {i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-600' : 'text-white/30'}">
									#{i + 1}
								</span>
								{#if project.image_url}
									<img src={project.image_url} alt="" class="w-12 h-12 rounded object-cover" />
								{:else}
									<div class="w-12 h-12 rounded bg-white/10"></div>
								{/if}
								<div>
									<p class="text-white font-medium">{project.name}</p>
									<p class="text-white/40 text-xs truncate max-w-md">{project.description}</p>
								</div>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-2xl font-bold text-white">{project.vote_count}</span>
								<span class="text-white/40 text-sm">votes</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	{/if}
</div>
