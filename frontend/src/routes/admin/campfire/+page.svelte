<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import {
		getCurrentUser,
		adminGetCampfireEvents,
		adminImportCampfireEvent,
		adminSyncCampfireEvent,
		adminSyncAllCampfireEvents,
		adminSyncProjectsToAirtable,
		type CockpitEvent
	} from '$lib/api';

	let events: CockpitEvent[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let busy = $state<string | null>(null);
	let filter = $state<'all' | 'active' | 'canceled'>('active');

	// Bulk operation progress
	let bulkOp = $state<{ type: 'import' | 'sync'; current: number; total: number; currentName: string } | null>(null);
	let airtableSyncing = $state(false);

	const filtered = $derived(
		events.filter((e) => {
			if (filter === 'active') return e.status === 'Active';
			if (filter === 'canceled') return e.status === 'Canceled';
			return true;
		})
	);

	const importedCount = $derived(events.filter((e) => e.already_imported).length);
	const notImportedActiveCount = $derived(
		events.filter((e) => e.status === 'Active' && !e.already_imported).length
	);
	const isBusy = $derived(busy !== null || bulkOp !== null || airtableSyncing);
	const bulkProgress = $derived(bulkOp ? Math.round((bulkOp.current / bulkOp.total) * 100) : 0);

	onMount(async () => {
		try {
			const user = await getCurrentUser();
			if (!user.is_superadmin) {
				goto('/admin');
				return;
			}
			events = await adminGetCampfireEvents();
		} catch (e: any) {
			error = e.message || 'Failed to load Cockpit events';
		} finally {
			loading = false;
		}
	});

	async function importEvent(cockpitEvent: CockpitEvent) {
		if (isBusy) return;
		busy = cockpitEvent.id;
		try {
			const result = await adminImportCampfireEvent(cockpitEvent.id);
			toast.success(
				`Imported "${cockpitEvent.displayName}" with ${result.attendees_imported} attendees`
			);
			cockpitEvent.already_imported = true;
			events = events;
		} catch (e: any) {
			toast.error(e.message || 'Import failed');
		} finally {
			busy = null;
		}
	}

	async function syncEvent(cockpitEvent: CockpitEvent) {
		if (isBusy) return;
		busy = cockpitEvent.id;
		try {
			const result = await adminSyncCampfireEvent(cockpitEvent.id);
			toast.success(
				`Updated "${cockpitEvent.displayName}" — ${result.attendees_synced} new attendees`
			);
		} catch (e: any) {
			toast.error(e.message || 'Update failed');
		} finally {
			busy = null;
		}
	}

	async function importAllActive() {
		if (isBusy) return;
		const toImport = events.filter((e) => e.status === 'Active' && !e.already_imported);
		if (toImport.length === 0) {
			toast.info('No new active events to import');
			return;
		}

		let successCount = 0;
		let errorCount = 0;
		let totalAttendees = 0;

		bulkOp = { type: 'import', current: 0, total: toImport.length, currentName: '' };

		for (let i = 0; i < toImport.length; i++) {
			const ce = toImport[i];
			bulkOp = { type: 'import', current: i, total: toImport.length, currentName: ce.displayName };
			try {
				const result = await adminImportCampfireEvent(ce.id);
				totalAttendees += result.attendees_imported;
				ce.already_imported = true;
				events = events;
				successCount++;
			} catch {
				errorCount++;
			}
		}

		bulkOp = null;

		if (errorCount > 0) {
			toast.warning(
				`Imported ${successCount} events (${totalAttendees} attendees, ${errorCount} errors)`
			);
		} else {
			toast.success(`Imported ${successCount} events — ${totalAttendees} attendees total`);
		}
	}

	async function syncToAirtable() {
		if (isBusy) return;
		airtableSyncing = true;
		try {
			const result = await adminSyncProjectsToAirtable();
			if (result.errors && result.errors.length > 0) {
				toast.warning(
					`Synced ${result.synced} of ${result.total} projects to Airtable (${result.errors.length} errors)`
				);
			} else {
				toast.success(`Synced ${result.synced} projects to Airtable`);
			}
		} catch (e: any) {
			toast.error(e.message || 'Airtable sync failed');
		} finally {
			airtableSyncing = false;
		}
	}

	async function syncAll() {
		if (isBusy) return;
		const toSync = events.filter((e) => e.already_imported);
		if (toSync.length === 0) {
			toast.info('No imported events to update');
			return;
		}

		bulkOp = { type: 'sync', current: 0, total: toSync.length, currentName: 'all events' };

		try {
			const result = await adminSyncAllCampfireEvents();
			bulkOp = null;

			const successCount = result.results.filter((r) => !r.error).length;
			const errorCount = result.results.filter((r) => r.error).length;
			const totalSynced = result.results.reduce((sum, r) => sum + r.synced, 0);

			if (errorCount > 0) {
				toast.warning(
					`Updated ${successCount} events (${totalSynced} new attendees, ${errorCount} errors). POC/RM set as admins.`
				);
			} else {
				toast.success(`Updated ${successCount} events — ${totalSynced} new attendees. POC/RM set as admins.`);
			}
		} catch (e: any) {
			bulkOp = null;
			toast.error(e.message || 'Bulk sync failed');
		}
	}
</script>

<div class="max-w-6xl">
	<div class="flex items-center justify-between mb-8">
		<div>
			<h1 class="text-3xl font-bold text-white">Campfire Job</h1>
			<p class="text-white/40 text-sm mt-1">
				Import and sync events from Cockpit into Podium
			</p>
		</div>
		<div class="flex gap-3 items-center">
			<button
				type="button"
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={isBusy}
				onclick={syncToAirtable}
			>
				{airtableSyncing ? 'Syncing to Airtable...' : 'Sync All Projects to Airtable'}
			</button>
			{#if notImportedActiveCount > 0}
				<button
					type="button"
					class="px-4 py-2 rounded-md text-sm font-medium transition-colors bg-green-500/20 text-green-400 hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={isBusy}
					onclick={importAllActive}
				>
					Import All Active ({notImportedActiveCount})
				</button>
			{/if}
			{#if importedCount > 0}
				<button
					type="button"
					class="px-4 py-2 rounded-md text-sm font-medium transition-colors bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={isBusy}
					onclick={syncAll}
				>
					Update All ({importedCount})
				</button>
			{/if}
			<div class="flex gap-1 bg-white/5 rounded-md p-0.5">
				<button
					type="button"
					class="px-3 py-1.5 rounded text-sm transition-colors {filter === 'active'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (filter = 'active')}
				>
					Active
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-sm transition-colors {filter === 'canceled'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (filter = 'canceled')}
				>
					Canceled
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-sm transition-colors {filter === 'all'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (filter = 'all')}
				>
					All
				</button>
			</div>
		</div>
	</div>

	{#if bulkOp}
		<div class="mb-6 rounded-lg border border-white/10 bg-white/5 p-4">
			<div class="flex items-center justify-between mb-2">
				<p class="text-sm text-white">
					{bulkOp.type === 'import' ? 'Importing' : 'Updating'}
					{bulkOp.currentName ? `"${bulkOp.currentName}"` : '...'}
					{#if bulkOp.type === 'sync'}
						<span class="text-white/40">(syncing participants + setting POC/RM as admins)</span>
					{/if}
				</p>
				<p class="text-xs text-white/40">
					{#if bulkOp.type === 'sync'}
						{bulkOp.total} events
					{:else}
						{bulkOp.current} / {bulkOp.total}
					{/if}
				</p>
			</div>
			<div class="h-2 rounded-full bg-white/10 overflow-hidden">
				{#if bulkOp.type === 'sync'}
					<div class="h-full rounded-full bg-blue-500 animate-pulse" style="width: 100%"></div>
				{:else}
					<div
						class="h-full rounded-full transition-all duration-300 bg-green-500"
						style="width: {bulkProgress}%"
					></div>
				{/if}
			</div>
		</div>
	{/if}

	{#if loading}
		<p class="text-white/60">Loading Cockpit events...</p>
	{:else if error}
		<p class="text-red-400">{error}</p>
	{:else if filtered.length === 0}
		<p class="text-white/60">No events match the current filter.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="text-left text-white/40 border-b border-white/10">
						<th class="pb-3 pr-4">Event</th>
						<th class="pb-3 pr-4">Location</th>
						<th class="pb-3 pr-4">Format</th>
						<th class="pb-3 pr-4">Status</th>
						<th class="pb-3 pr-4 text-right">Participants</th>
						<th class="pb-3 pr-4">POC</th>
						<th class="pb-3 pr-4">RM</th>
						<th class="pb-3"></th>
					</tr>
				</thead>
				<tbody>
					{#each filtered as event}
						<tr class="border-b border-white/5 hover:bg-white/5">
							<td class="py-3 pr-4">
								<span class="text-white font-medium">{event.displayName}</span>
							</td>
							<td class="py-3 pr-4 text-white/60">
								{[event.city, event.country].filter(Boolean).join(', ') || '—'}
							</td>
							<td class="py-3 pr-4 text-white/60">{event.format || '—'}</td>
							<td class="py-3 pr-4">
								<span
									class="px-2 py-0.5 rounded text-xs {event.status === 'Active'
										? 'bg-green-500/20 text-green-400'
										: event.status === 'Canceled'
											? 'bg-red-500/20 text-red-400'
											: 'bg-yellow-500/20 text-yellow-400'}"
								>
									{event.status}
								</span>
							</td>
							<td class="py-3 pr-4 text-right text-white/60">
								{event.numParticipants}
								{#if event.estimatedAttendeesCount > 0}
									<span class="text-white/30">/ {event.estimatedAttendeesCount}</span>
								{/if}
							</td>
							<td class="py-3 pr-4 text-white/60 text-xs">
								{event.pocName?.join(', ') || '—'}
							</td>
							<td class="py-3 pr-4 text-white/60 text-xs">
								{event.rmName?.join(', ') || '—'}
							</td>
							<td class="py-3">
								<div class="flex gap-2">
									{#if event.already_imported}
										<button
											type="button"
											class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors
												{busy === event.id
												? 'bg-blue-500/10 text-blue-300 cursor-wait'
												: 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'}"
											disabled={isBusy}
											onclick={() => syncEvent(event)}
										>
											{busy === event.id ? 'Updating...' : 'Update'}
										</button>
									{:else}
										<button
											type="button"
											class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors
												{busy === event.id
												? 'bg-white/5 text-white/30 cursor-wait'
												: 'bg-white text-[#111] hover:bg-white/90'}"
											disabled={isBusy}
											onclick={() => importEvent(event)}
										>
											{busy === event.id ? 'Importing...' : 'Import'}
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<p class="text-white/30 text-xs mt-4">
			Showing {filtered.length} of {events.length} events
			({importedCount} imported)
		</p>
	{/if}
</div>
