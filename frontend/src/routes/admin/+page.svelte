<script lang="ts">
	import { onMount } from 'svelte';
	import { adminListEvents, type ApiAdminEvent } from '$lib/api';

	let events: ApiAdminEvent[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	let statusFilter = $state<'all' | 'enabled' | 'disabled'>('all');
	let typeFilter = $state<'all' | 'campfire' | 'other'>('all');

	const filtered = $derived(
		events.filter((e) => {
			if (search) {
				const q = search.toLowerCase();
				if (!e.name.toLowerCase().includes(q) && !e.slug.toLowerCase().includes(q)) {
					return false;
				}
			}
			if (statusFilter === 'enabled' && !e.enabled) return false;
			if (statusFilter === 'disabled' && e.enabled) return false;
			if (typeFilter === 'campfire' && !e.feature_flags_csv.includes('campfire')) return false;
			if (typeFilter === 'other' && e.feature_flags_csv.includes('campfire')) return false;
			return true;
		})
	);

	onMount(async () => {
		try {
			events = await adminListEvents();
		} catch (e: any) {
			error = e.message || 'Failed to load events';
		} finally {
			loading = false;
		}
	});
</script>

<div class="max-w-4xl">
	<div class="flex items-center justify-between mb-6">
		<h1 class="text-3xl font-bold text-white">Events</h1>
		<a
			href="/admin/events/create"
			class="px-4 py-2 bg-white text-[#111] rounded-md text-sm font-medium hover:bg-white/90 transition-colors"
		>
			Create Event
		</a>
	</div>

	{#if !loading && !error && events.length > 0}
		<div class="flex items-center gap-3 mb-6">
			<input
				type="text"
				placeholder="Search events..."
				bind:value={search}
				class="flex-1 px-3 py-2 rounded-md bg-white/5 border border-white/10 text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-white/20"
			/>
			<div class="flex gap-1 bg-white/5 rounded-md p-0.5">
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {statusFilter === 'all'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (statusFilter = 'all')}
				>
					All
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {statusFilter === 'enabled'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (statusFilter = 'enabled')}
				>
					Enabled
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {statusFilter === 'disabled'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (statusFilter = 'disabled')}
				>
					Disabled
				</button>
			</div>
			<div class="flex gap-1 bg-white/5 rounded-md p-0.5">
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {typeFilter === 'all'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (typeFilter = 'all')}
				>
					All
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {typeFilter === 'campfire'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (typeFilter = 'campfire')}
				>
					Campfire
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {typeFilter === 'other'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (typeFilter = 'other')}
				>
					Other
				</button>
			</div>
		</div>
	{/if}

	{#if loading}
		<p class="text-white/60">Loading events...</p>
	{:else if error}
		<p class="text-red-400">{error}</p>
	{:else if events.length === 0}
		<div class="text-center py-12">
			<p class="text-white/60 text-lg">No events yet</p>
			<p class="text-white/40 text-sm mt-2">Create your first event to get started</p>
		</div>
	{:else if filtered.length === 0}
		<p class="text-white/40 text-sm">No events match your filters.</p>
	{:else}
		<div class="flex flex-col gap-3">
			{#each filtered as event}
				<a
					href="/admin/events/{event.id}"
					class="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
				>
					<div class="flex flex-col gap-1">
						<span class="text-white font-medium">{event.name}</span>
						<span class="text-white/40 text-sm">/{event.slug}</span>
					</div>
					<div class="flex items-center gap-6 text-sm text-white/60">
						<div class="flex flex-col items-center">
							<span class="text-white font-medium">{event.attendee_count}</span>
							<span class="text-xs">attendees</span>
						</div>
						<div class="flex flex-col items-center">
							<span class="text-white font-medium">{event.project_count}</span>
							<span class="text-xs">projects</span>
						</div>
						<div class="flex flex-col items-center">
							<span class="text-white font-medium">{event.vote_count}</span>
							<span class="text-xs">votes</span>
						</div>
						<div class="flex items-center gap-2">
							{#if event.enabled}
								<span class="px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">Enabled</span>
							{/if}
							{#if event.votable}
								<span class="px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">Voting</span>
							{/if}
							{#if event.leaderboard_enabled}
								<span class="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 text-xs">Leaderboard</span>
							{/if}
						</div>
						<span class="text-white/30">→</span>
					</div>
				</a>
			{/each}
		</div>
		<p class="text-white/30 text-xs mt-4">
			Showing {filtered.length} of {events.length} events
		</p>
	{/if}
</div>
