<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import {
		getCurrentUser,
		adminSyncAllHavenEvents,
		adminSyncHavenProjectsToAirtable,
		type HavenSyncResult
	} from '$lib/api';

	let loading = $state(true);
	let syncing = $state(false);
	let airtableSyncing = $state(false);
	let results = $state<HavenSyncResult[] | null>(null);
	let filter = $state<'all' | 'problems'>('all');

	const isBusy = $derived(syncing || airtableSyncing);
	const filtered = $derived(
		(results ?? []).filter((r) => filter === 'all' || r.error || r.disabled)
	);

	onMount(async () => {
		try {
			const user = await getCurrentUser();
			if (!user.is_superadmin) {
				goto('/admin');
				return;
			}
		} catch {
			goto('/admin');
			return;
		} finally {
			loading = false;
		}
	});

	async function syncAll() {
		if (isBusy) return;
		syncing = true;
		try {
			const result = await adminSyncAllHavenEvents();
			results = result.results;
			if (result.results.some((r) => r.error)) {
				toast.warning(result.message);
			} else {
				toast.success(result.message);
			}
		} catch (e: any) {
			toast.error(e.message || 'Haven sync failed');
		} finally {
			syncing = false;
		}
	}

	async function syncToAirtable() {
		if (isBusy) return;
		airtableSyncing = true;
		try {
			const result = await adminSyncHavenProjectsToAirtable();
			if (result.errors && result.errors.length > 0) {
				toast.warning(`${result.message} (${result.errors.length} batches failed)`);
			} else {
				toast.success(result.message);
			}
		} catch (e: any) {
			toast.error(e.message || 'Airtable sync failed');
		} finally {
			airtableSyncing = false;
		}
	}
</script>

<div class="max-w-6xl">
	<div class="flex items-center justify-between mb-8">
		<div>
			<h1 class="text-3xl font-bold text-white">Haven</h1>
			<p class="text-white/40 text-sm mt-1">
				Import Haven events and their rosters from Haven's Airtable, and send finished projects back
			</p>
		</div>
		<div class="flex gap-3 items-center">
			<button
				type="button"
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={isBusy || loading}
				onclick={syncToAirtable}
			>
				{airtableSyncing ? 'Syncing to Airtable...' : 'Send Closed Events to Airtable'}
			</button>
			<button
				type="button"
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={isBusy || loading}
				onclick={syncAll}
			>
				{syncing ? 'Syncing (takes about a minute)...' : 'Import & Sync All Events'}
			</button>
		</div>
	</div>

	<div class="mb-6 rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-white/60 flex flex-col gap-1">
		<p>
			<span class="text-white/80">Import & Sync</span> creates a Podium event for every Active Haven
			event, sets its POC and EM as the event's POC and RM, and adds its live participants (not
			withdrawn or deleted) to the roster. Events that are no longer Active are disabled. Safe to run
			again: it never removes anyone.
		</p>
		<p>
			Haven events are roster-only: people can't join them on their own, so someone who signed up
			late needs a sync (any event admin can run one from the event page) before they can submit or
			vote.
		</p>
		<p>
			<span class="text-white/80">Send Closed Events</span> upserts one YSWS Project Submission per
			project member for every Haven event whose voting is closed.
		</p>
	</div>

	{#if results}
		<div class="flex items-center justify-between mb-3">
			<p class="text-white/60 text-sm">{results.length} events in the last sync</p>
			<div class="flex gap-1 bg-white/5 rounded-md p-0.5">
				<button
					type="button"
					class="px-3 py-1.5 rounded text-sm transition-colors {filter === 'all'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (filter = 'all')}
				>
					All
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-sm transition-colors {filter === 'problems'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (filter = 'problems')}
				>
					Errors & disabled
				</button>
			</div>
		</div>
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="text-left text-white/40 border-b border-white/10">
						<th class="pb-3 pr-4">Event</th>
						<th class="pb-3 pr-4">Slug</th>
						<th class="pb-3 pr-4">Result</th>
						<th class="pb-3 pr-4 text-right">Attendees added</th>
					</tr>
				</thead>
				<tbody>
					{#each filtered as r (r.slug)}
						<tr class="border-b border-white/5 hover:bg-white/5">
							<td class="py-3 pr-4">
								{#if r.event_id}
									<a href="/admin/events/{r.event_id}" class="text-white font-medium hover:underline">{r.name}</a>
								{:else}
									<span class="text-white font-medium">{r.name}</span>
								{/if}
							</td>
							<td class="py-3 pr-4 text-white/60">{r.slug}</td>
							<td class="py-3 pr-4">
								{#if r.error}
									<span class="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">{r.error}</span>
								{:else if r.disabled}
									<span class="px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-400">Disabled</span>
								{:else if r.created}
									<span class="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">Imported</span>
								{:else}
									<span class="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400">Updated</span>
								{/if}
							</td>
							<td class="py-3 pr-4 text-right text-white/60">{r.attendees_added}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
