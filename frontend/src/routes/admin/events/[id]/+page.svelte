<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
	import { adminGetEvent, adminUpdateEvent, adminDeleteEvent, adminSyncFromCockpit, adminSyncEventToAirtable, type ApiAdminEvent, type ApiUser } from '$lib/api';
	import { toast } from 'svelte-sonner';

	const getAdminUser = getContext<() => ApiUser | null>('adminUser');

	const eventId = $derived(page.params.id ?? '');

	let event: ApiAdminEvent | null = $state(null);
	const isCampfire = $derived((event as ApiAdminEvent | null)?.feature_flags_csv?.includes('campfire') ?? false);
	const isFlagship = $derived((event as ApiAdminEvent | null)?.feature_flags_csv?.includes('flagship') ?? false);
	const isPocOrRm = $derived.by(() => {
		const u = getAdminUser();
		if (!u || !event) return false;
		if (u.is_superadmin) return false;
		return event.poc_id === u.id || event.rm_id === u.id;
	});
	let loading = $state(true);
	let error = $state('');
	let saving = $state(false);
	let deleting = $state(false);
	let confirmDelete = $state(false);
	let syncing = $state(false);
	let syncResult = $state('');
	let airtableSyncing = $state(false);

	onMount(async () => {
		try {
			event = await adminGetEvent(eventId);
		} catch (e: any) {
			error = e.message || 'Failed to load event';
		} finally {
			loading = false;
		}
	});

	const normalStages = [
		{ id: 'draft', label: 'Draft', description: 'Event is hidden from the public' },
		{ id: 'live', label: 'Live', description: 'Visible on homepage, accepting submissions' },
		{ id: 'voting', label: 'Voting', description: 'Attendees can vote on projects' },
		{ id: 'closed', label: 'Closed', description: 'Voting is closed' },
		{ id: 'results', label: 'Results', description: 'Leaderboard is public' },
	] as const;

	const flagshipStages = [
		{ id: 'draft', label: 'Draft', description: 'Event is hidden from the public' },
		{ id: 'live', label: 'Live', description: 'Visible on homepage, accepting submissions' },
		{ id: 'results', label: 'Results', description: 'Leaderboard is public (admin-set points)' },
	] as const;

	type Stage = 'draft' | 'live' | 'voting' | 'closed' | 'results';

	const stages = $derived(isFlagship ? flagshipStages : normalStages);

	const stageFlags: Record<string, Record<string, boolean>> = {
		draft:   { enabled: false, votable: false, voting_closed: false, leaderboard_enabled: false },
		live:    { enabled: true,  votable: false, voting_closed: false, leaderboard_enabled: false },
		voting:  { enabled: true,  votable: true,  voting_closed: false, leaderboard_enabled: false },
		closed:  { enabled: true,  votable: true,  voting_closed: true,  leaderboard_enabled: false },
		results: { enabled: true,  votable: true,  voting_closed: true,  leaderboard_enabled: true },
	};

	// Flagship results: no votable, just leaderboard
	const flagshipStageFlags: Record<string, Record<string, boolean>> = {
		draft:   { enabled: false, votable: false, voting_closed: false, leaderboard_enabled: false },
		live:    { enabled: true,  votable: false, voting_closed: false, leaderboard_enabled: false },
		results: { enabled: true,  votable: false, voting_closed: true,  leaderboard_enabled: true },
	};

	const currentStage: Stage = $derived.by(() => {
		if (!event) return 'draft';
		if (isFlagship) {
			if (event.leaderboard_enabled) return 'results';
			if (event.enabled) return 'live';
			return 'draft';
		}
		if (event.leaderboard_enabled && event.voting_closed) return 'results';
		if (event.voting_closed) return 'closed';
		if (event.votable) return 'voting';
		if (event.enabled) return 'live';
		return 'draft';
	});

	const currentStageIndex = $derived(stages.findIndex((s) => s.id === currentStage));

	async function setStage(stage: string) {
		if (!event || saving) return;
		saving = true;
		error = '';
		const flags = isFlagship ? flagshipStageFlags[stage] : stageFlags[stage];
		try {
			event = await adminUpdateEvent(eventId, flags);
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}

	async function toggleField(field: string, value: boolean) {
		if (!event) return;
		saving = true;
		try {
			event = await adminUpdateEvent(eventId, { [field]: value });
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}

	async function handleSync() {
		syncing = true;
		syncResult = '';
		error = '';
		try {
			const result = await adminSyncFromCockpit(eventId);
			syncResult = `Synced ${result.attendees_synced} new attendee${result.attendees_synced === 1 ? '' : 's'}`;
			event = await adminGetEvent(eventId);
		} catch (e: any) {
			error = e.message || 'Failed to sync from Cockpit';
		} finally {
			syncing = false;
		}
	}

	async function handleAirtableSync() {
		if (airtableSyncing) return;
		airtableSyncing = true;
		try {
			const result = await adminSyncEventToAirtable(eventId);
			if (result.errors && result.errors.length > 0) {
				toast.warning(
					`Synced ${result.synced} of ${result.total} records to Airtable (${result.errors.length} errors)`
				);
			} else {
				toast.success(`Synced ${result.synced} records to Airtable`);
			}
		} catch (e: any) {
			toast.error(e.message || 'Airtable sync failed');
		} finally {
			airtableSyncing = false;
		}
	}

	async function handleDelete() {
		if (!confirmDelete) {
			confirmDelete = true;
			return;
		}
		deleting = true;
		try {
			await adminDeleteEvent(eventId);
			goto('/admin');
		} catch (e: any) {
			error = e.message;
			deleting = false;
		}
	}
</script>

{#if loading}
	<p class="text-white/60">Loading...</p>
{:else if error && !event}
	<p class="text-red-400">{error}</p>
{:else if event}
	<div class="max-w-4xl">
		<!-- Header -->
		<div class="flex items-center justify-between mb-8">
			<div>
				<h1 class="text-3xl font-bold text-white">{event.name}</h1>
				<p class="text-white/40 text-sm mt-1">/{event.slug}</p>
			</div>
			<a
				href="/{event.slug}"
				target="_blank"
				class="px-4 py-2 border border-white/20 text-white/60 rounded-md text-sm hover:text-white hover:border-white/40 transition-colors"
			>
				View Public Page →
			</a>
		</div>

		<!-- Stats -->
		<div class="grid grid-cols-3 gap-4 mb-8">
			<div class="p-4 rounded-lg bg-white/5 border border-white/10">
				<p class="text-3xl font-bold text-white">{event.attendee_count}</p>
				<p class="text-white/40 text-sm">Attendees</p>
			</div>
			<div class="p-4 rounded-lg bg-white/5 border border-white/10">
				<p class="text-3xl font-bold text-white">{event.project_count}</p>
				<p class="text-white/40 text-sm">Projects</p>
			</div>
			{#if !isFlagship}
				<div class="p-4 rounded-lg bg-white/5 border border-white/10">
					<p class="text-3xl font-bold text-white">{event.vote_count}</p>
					<p class="text-white/40 text-sm">Votes</p>
				</div>
			{:else}
				<div class="p-4 rounded-lg bg-white/5 border border-white/10">
					<p class="text-3xl font-bold text-white">Flagship</p>
					<p class="text-white/40 text-sm">Admin-judged</p>
				</div>
			{/if}
		</div>

		<!-- Cockpit Sync (campfire events only) -->
		{#if isCampfire}
			<div class="flex items-center gap-4 p-4 rounded-lg bg-white/5 border border-white/10 mb-6">
				<div class="flex-1">
					<p class="text-sm text-white/80 font-medium">Cockpit Sync</p>
					<p class="text-xs text-white/40">Pull new participants and updated info from Cockpit</p>
				</div>
				{#if syncResult}
					<p class="text-sm text-green-400">{syncResult}</p>
				{/if}
				<button
					type="button"
					onclick={handleSync}
					disabled={syncing}
					class="px-4 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-md text-sm hover:bg-blue-500/30 transition-colors disabled:opacity-50 shrink-0"
				>
					{syncing ? 'Syncing...' : 'Sync from Cockpit'}
				</button>
			</div>
			<div class="flex items-center gap-4 p-4 rounded-lg bg-white/5 border border-white/10 mb-6">
				<div class="flex-1">
					<p class="text-sm text-white/80 font-medium">Airtable Sync</p>
					<p class="text-xs text-white/40">Sync all projects and participants from this event to Airtable</p>
				</div>
				<button
					type="button"
					onclick={handleAirtableSync}
					disabled={airtableSyncing}
					class="px-4 py-2 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-md text-sm hover:bg-purple-500/30 transition-colors disabled:opacity-50 shrink-0"
				>
					{airtableSyncing ? 'Syncing to Airtable...' : 'Sync All Projects to Airtable'}
				</button>
			</div>
		{/if}

		<!-- Event Stage -->
		<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10 mb-6">
			<h2 class="text-lg font-medium text-white">Event Stage</h2>

			<div class="flex flex-col gap-1.5">
				<!-- Dots + connectors -->
				<div class="flex items-center">
					{#each stages as stage, i}
						{@const isActive = i === currentStageIndex}
						{@const isPast = i < currentStageIndex}
						{#if i > 0}
							<div
								class="h-0.5 flex-1 transition-colors"
								style="background-color: {isPast || isActive ? 'rgb(96 165 250)' : 'rgb(255 255 255 / 0.1)'};"
							></div>
						{/if}
						<button
							type="button"
							disabled={saving}
							onclick={() => setStage(stage.id)}
							class="shrink-0 group disabled:opacity-50"
						>
							<div
								class="w-4 h-4 rounded-full border-2 transition-colors {isActive ? 'scale-125' : 'group-hover:scale-110'}"
								style="border-color: {isPast || isActive ? 'rgb(96 165 250)' : 'rgb(255 255 255 / 0.3)'}; background-color: {isActive ? 'rgb(96 165 250)' : isPast ? 'rgb(96 165 250 / 0.3)' : 'transparent'};"
							></div>
						</button>
					{/each}
				</div>
				<!-- Labels -->
				<div class="flex justify-between">
					{#each stages as stage, i}
						{@const isActive = i === currentStageIndex}
						{@const isPast = i < currentStageIndex}
						<button
							type="button"
							disabled={saving}
							onclick={() => setStage(stage.id)}
							class="text-xs transition-colors disabled:opacity-50 {isActive ? 'text-blue-400 font-medium' : isPast ? 'text-white/60' : 'text-white/30 hover:text-white/50'}"
							style="width: {100 / stages.length}%; text-align: {i === 0 ? 'left' : i === stages.length - 1 ? 'right' : 'center'};"
						>
							{stage.label}
						</button>
					{/each}
				</div>
			</div>

			<p class="text-xs text-white/40">{stages[currentStageIndex].description}</p>
		</div>

		<!-- Settings -->
		<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10 mb-6">
			<h2 class="text-lg font-medium text-white">Settings</h2>

			{#if !isCampfire}
				<label class="flex items-center justify-between cursor-pointer">
					<span class="text-sm text-white/80">Demo Links Optional</span>
					<input
						type="checkbox"
						checked={event.demo_links_optional}
						onchange={() => toggleField('demo_links_optional', !event!.demo_links_optional)}
						class="w-5 h-5 rounded cursor-pointer"
					/>
				</label>
			{/if}

			<label class="flex items-center justify-between cursor-pointer">
				<span class="text-sm text-white/80">YSWS Checks Enabled</span>
				<input
					type="checkbox"
					checked={event.ysws_checks_enabled}
					onchange={() => toggleField('ysws_checks_enabled', !event!.ysws_checks_enabled)}
					class="w-5 h-5 rounded cursor-pointer"
				/>
			</label>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<span class="text-sm text-white/80">Disable Itch.io Verifications</span>
					<p class="text-xs text-white/40">Skip itch.io URL and playability checks for this event</p>
				</div>
				<input
					type="checkbox"
					checked={event.itch_verification_disabled}
					onchange={() => toggleField('itch_verification_disabled', !event!.itch_verification_disabled)}
					class="w-5 h-5 rounded cursor-pointer"
				/>
			</label>
		</div>

		<!-- Navigation -->
		<div class="grid grid-cols-2 gap-4 mb-8">
			<a
				href="/admin/events/{eventId}/stats"
				class="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors col-span-2"
			>
				<p class="text-white font-medium">Event Stats</p>
				<p class="text-white/40 text-sm mt-1">Submission tracking and vote leaderboard</p>
			</a>
			<a
				href="/admin/events/{eventId}/theme"
				class="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
			>
				<p class="text-white font-medium">Theme Editor</p>
				<p class="text-white/40 text-sm mt-1">Customize colors, fonts, and background</p>
			</a>
			<a
				href="/admin/events/{eventId}/projects"
				class="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
			>
				<p class="text-white font-medium">Projects ({event.project_count})</p>
				<p class="text-white/40 text-sm mt-1">View, edit, and manage projects</p>
			</a>
			<a
				href="/admin/events/{eventId}/attendees"
				class="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
			>
				<p class="text-white font-medium">Attendees ({event.attendee_count})</p>
				<p class="text-white/40 text-sm mt-1">View and manage attendees</p>
			</a>
			<a
				href="/admin/events/{eventId}/leaderboard"
				class="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
			>
				<p class="text-white font-medium">Leaderboard</p>
				<p class="text-white/40 text-sm mt-1">{isFlagship ? 'Set project rankings manually' : 'View project rankings'}</p>
			</a>
		</div>

		<!-- Danger Zone -->
		{#if !isPocOrRm}
			<div class="p-6 rounded-lg border border-red-500/30 bg-red-500/5">
				<h2 class="text-lg font-medium text-red-400 mb-4">Danger Zone</h2>
				{#if error}
					<p class="text-red-400 text-sm mb-3">{error}</p>
				{/if}
				<button
					type="button"
					onclick={handleDelete}
					disabled={deleting}
					class="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-md text-sm hover:bg-red-500/30 transition-colors disabled:opacity-50"
				>
					{deleting ? 'Deleting...' : confirmDelete ? 'Click again to confirm deletion' : 'Delete Event'}
				</button>
			</div>
		{/if}
	</div>
{/if}
