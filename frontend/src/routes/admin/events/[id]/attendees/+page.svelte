<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { adminGetAttendees, adminAddAttendee, adminRemoveAttendee, type ApiAttendee } from '$lib/api';

	const eventId = $derived(page.params.id ?? '');

	let attendees: ApiAttendee[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let removingId: string | null = $state(null);
	let searchQuery = $state('');
	let addEmail = $state('');
	let adding = $state(false);
	let shippedFilter = $state<'all' | 'shipped' | 'not_shipped'>('all');

	let filtered = $derived(
		attendees.filter((a) => {
			if (shippedFilter === 'shipped' && !a.has_project) return false;
			if (shippedFilter === 'not_shipped' && a.has_project) return false;
			return `${a.email} ${a.display_name}`
				.toLowerCase()
				.includes(searchQuery.toLowerCase());
		})
	);

	const shippedCount = $derived(attendees.filter((a) => a.has_project).length);

	onMount(async () => {
		try {
			attendees = await adminGetAttendees(eventId);
		} catch (e: any) {
			error = e.message || 'Failed to load attendees';
		} finally {
			loading = false;
		}
	});

	async function handleAdd() {
		if (!addEmail.trim()) return;
		adding = true;
		error = '';
		try {
			const attendee = await adminAddAttendee(eventId, addEmail.trim());
			attendees = [...attendees, attendee];
			addEmail = '';
		} catch (e: any) {
			error = e.message || 'Failed to add attendee';
		} finally {
			adding = false;
		}
	}

	async function handleRemove(userId: string) {
		if (removingId !== userId) {
			removingId = userId;
			return;
		}
		try {
			await adminRemoveAttendee(eventId, userId);
			attendees = attendees.filter((a) => a.user_id !== userId);
			removingId = null;
		} catch (e: any) {
			error = e.message || 'Failed to remove attendee';
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
		<h1 class="text-3xl font-bold text-white">Attendees</h1>
		<span class="text-white/40 text-sm">({attendees.length})</span>
	</div>

	{#if loading}
		<p class="text-white/60">Loading...</p>
	{:else if error && attendees.length === 0}
		<p class="text-red-400">{error}</p>
	{:else}
		{#if error}
			<p class="text-red-400 text-sm mb-4">{error}</p>
		{/if}

		<form
			onsubmit={(e) => { e.preventDefault(); handleAdd(); }}
			class="flex gap-2 mb-4"
		>
			<input
				type="email"
				bind:value={addEmail}
				placeholder="Add attendee by email..."
				class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm placeholder:text-white/30"
			/>
			<button
				type="submit"
				disabled={adding || !addEmail.trim()}
				class="px-4 py-2 rounded-md bg-white/10 text-white border border-white/20 text-sm hover:bg-white/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
			>
				{adding ? 'Adding...' : 'Add'}
			</button>
		</form>

		<div class="flex items-center gap-3 mb-4">
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search attendees..."
				class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm placeholder:text-white/30"
			/>
			<div class="flex gap-1 bg-white/5 rounded-md p-0.5">
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {shippedFilter === 'all'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (shippedFilter = 'all')}
				>
					All
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {shippedFilter === 'shipped'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (shippedFilter = 'shipped')}
				>
					Shipped ({shippedCount})
				</button>
				<button
					type="button"
					class="px-3 py-1.5 rounded text-xs transition-colors {shippedFilter === 'not_shipped'
						? 'bg-white/10 text-white'
						: 'text-white/40 hover:text-white'}"
					onclick={() => (shippedFilter = 'not_shipped')}
				>
					Not shipped
				</button>
			</div>
		</div>

		{#if filtered.length === 0}
			<p class="text-white/60 text-center py-12">No attendees found</p>
		{:else}
			<div class="flex flex-col gap-2">
				{#each filtered as attendee}
					<div class="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
						<div class="flex items-center gap-2">
							<div>
								<p class="text-white text-sm">
									{attendee.display_name || attendee.email}
								</p>
								{#if attendee.display_name}
									<p class="text-white/40 text-xs">{attendee.email}</p>
								{/if}
							</div>
							{#if attendee.has_project}
								<span class="px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">Shipped</span>
							{/if}
						</div>
						<button
							type="button"
							onclick={() => handleRemove(attendee.user_id)}
							class="px-3 py-1.5 border border-red-500/30 text-red-400/60 rounded-md text-xs hover:text-red-400 hover:border-red-500/50 transition-colors"
						>
							{removingId === attendee.user_id ? 'Confirm?' : 'Remove'}
						</button>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
