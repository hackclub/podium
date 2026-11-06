<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { EventTheme } from '$lib/theme';
	import {
		getMyProjects, getProject, lookupTeammate,
		ownerAddCollaborator, ownerRemoveCollaborator,
		getCurrentUser,
		type ApiEvent, type ApiProjectCollaborator, type TeammateData
	} from '$lib/api';
	import { isLoggedIn } from '$lib/auth';
	import Input from '$lib/forms/Input.svelte';
	import Label from '$lib/forms/Label.svelte';
	import Button from '$lib/forms/Button.svelte';
	import ProfileGate from '$lib/forms/ProfileGate.svelte';

	const eventStore = getContext<Writable<ApiEvent | null>>('event');
	const eventThemeStore = getContext<Writable<EventTheme | null>>('eventTheme');
	const eventIdStore = getContext<Writable<string | null>>('eventId');

	let eventData: ApiEvent | null = $state(null);
	let eventTheme: EventTheme | null = $state(null);
	let eventId: string | null = $state(null);

	$effect(() => {
		const unsub1 = eventStore.subscribe((v) => (eventData = v));
		const unsub2 = eventThemeStore.subscribe((v) => (eventTheme = v));
		const unsub3 = eventIdStore.subscribe((v) => (eventId = v));
		return () => { unsub1(); unsub2(); unsub3(); };
	});

	const slug = $derived(page.params.slug);

	let loading = $state(true);
	let projectId: string | null = $state(null);
	let collaborators: ApiProjectCollaborator[] = $state([]);
	let error = $state('');

	// Add teammate state
	let emailInput = $state('');
	let lookingUp = $state(false);
	let pendingTeammate: (TeammateData & { missing_fields: string[] }) | null = $state(null);
	let addError = $state('');
	let saving = $state(false);

	const fieldLabels: Record<string, string> = {
		first_name: 'First Name',
		last_name: 'Last Name',
		phone: 'Phone Number',
		street_1: 'Street Address',
		city: 'City',
		state: 'State / Province',
		zip_code: 'ZIP / Postal Code',
		country: 'Country',
		dob: 'Date of Birth',
	};

	const fieldPlaceholders: Record<string, string> = {
		first_name: 'Jane',
		last_name: 'Doe',
		phone: '+1 555 123 4567',
		street_1: '123 Main St',
		city: 'San Francisco',
		state: 'CA',
		zip_code: '94102',
		country: 'United States',
		dob: '',
	};

	const fieldTypes: Record<string, string> = {
		phone: 'tel',
		dob: 'date',
	};

	onMount(async () => {
		if (!isLoggedIn()) {
			goto(`/${slug}`);
			return;
		}

		try {
			const [user, projects] = await Promise.all([
				getCurrentUser(),
				getMyProjects(),
			]);

			const currentEventId = eventId;
			const owned = projects.find((p) => p.event_id === currentEventId && p.owner_id === user.id);
			if (!owned) {
				loading = false;
				return;
			}

			projectId = owned.id;
			const full = await getProject(owned.id);
			collaborators = full.collaborators;
		} catch (e: any) {
			error = e.message || 'Failed to load project';
		} finally {
			loading = false;
		}
	});

	async function handleLookup() {
		const email = emailInput.trim().toLowerCase();
		if (!email || !email.includes('@')) return;

		lookingUp = true;
		addError = '';
		pendingTeammate = null;

		try {
			const result = await lookupTeammate(email);

			if (result.missing_fields.length === 0) {
				// No missing fields — add immediately
				await addCollaborator({ email });
				emailInput = '';
			} else {
				// Show missing fields form
				pendingTeammate = { email, missing_fields: result.missing_fields };
			}
		} catch (e: any) {
			addError = e.message || 'Failed to look up teammate';
		} finally {
			lookingUp = false;
		}
	}

	async function savePendingTeammate() {
		if (!pendingTeammate || !projectId) return;
		saving = true;
		addError = '';

		try {
			const data: TeammateData = { email: pendingTeammate.email };
			for (const f of pendingTeammate.missing_fields) {
				const val = (pendingTeammate as any)[f];
				if (val) (data as any)[f] = val;
			}
			await addCollaborator(data);
			pendingTeammate = null;
			emailInput = '';
		} catch (e: any) {
			addError = e.message || 'Failed to add teammate';
		} finally {
			saving = false;
		}
	}

	async function addCollaborator(data: TeammateData) {
		if (!projectId) return;
		const collab = await ownerAddCollaborator(projectId, data);
		collaborators = [...collaborators, collab];
	}

	async function removeCollaborator(userId: string) {
		if (!projectId) return;
		try {
			await ownerRemoveCollaborator(projectId, userId);
			collaborators = collaborators.filter((c) => c.user_id !== userId);
		} catch (e: any) {
			error = e.message || 'Failed to remove teammate';
		}
	}

	function updatePendingField(field: string, value: string) {
		if (!pendingTeammate) return;
		pendingTeammate = { ...pendingTeammate, [field]: value };
	}

	function handleEmailKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleLookup();
		}
	}

	const isTeamEditAllowed = $derived(
		(eventData as ApiEvent | null)?.votable || (eventData as ApiEvent | null)?.voting_closed || false
	);
</script>

{#if eventTheme}
<ProfileGate {eventTheme}>
<main class="flex flex-1 flex-col px-4">
<div class="flex flex-1 items-center justify-center py-12">
	{#if loading}
		<p class="text-white/60 drop-shadow-md">Loading...</p>
	{:else if !isTeamEditAllowed}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-(--edge) px-6 py-10 drop-shadow-md text-center"
			style="font-family: {eventTheme.font};"
		>
			<div class="absolute inset-0 bg-(--surface)"></div>
			<div class="relative flex flex-col items-center gap-3">
				<p class="font-(family-name:--heading-font) text-3xl text-(--ink) drop-shadow-(--shade)">Team editing is not available yet</p>
				<p class="text-lg text-(--ink)/70 drop-shadow-(--shade)">You can edit your team once submissions close.</p>
			</div>
		</div>
	{:else if !projectId}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-(--edge) px-6 py-10 drop-shadow-md text-center"
			style="font-family: {eventTheme.font};"
		>
			<div class="absolute inset-0 bg-(--surface)"></div>
			<div class="relative flex flex-col items-center gap-3">
				<p class="font-(family-name:--heading-font) text-3xl text-(--ink) drop-shadow-(--shade)">No project found</p>
				<p class="text-lg text-(--ink)/70 drop-shadow-(--shade)">You don't own a project in this event.</p>
				<button
					type="button"
					onclick={() => goto(`/${slug}/vote`)}
					class="mt-2 text-md text-(--ink)/70 underline drop-shadow-(--shade) cursor-pointer transition-colors ease-in-out duration-125 hover:text-(--accent-ink)"
				>
					Back to voting
				</button>
			</div>
		</div>
	{:else}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-(--edge) px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div class="absolute inset-0 rounded-lg bg-(--surface)"></div>

			<div class="relative flex flex-col gap-4">
				<p class="font-(family-name:--heading-font) text-2xl text-(--ink) drop-shadow-(--shade)">Manage Teammates</p>

				{#if collaborators.length === 0}
					<p class="text-sm text-(--ink)/50 drop-shadow-(--shade)">No teammates added yet.</p>
				{:else}
					<div class="flex flex-col gap-2">
						{#each collaborators as collab}
							<div class="flex items-center justify-between rounded-xl border-2 border-(--line)/30 p-3">
								<p class="text-sm text-(--ink)/70 drop-shadow-(--shade)">{collab.display_name}</p>
								<button
									type="button"
									onclick={() => removeCollaborator(collab.user_id)}
									class="text-(--ink)/50 hover:text-(--ink) text-sm cursor-pointer transition-colors"
								>
									Remove
								</button>
							</div>
						{/each}
					</div>
				{/if}

				{#if pendingTeammate}
					<div class="rounded-xl border-2 border-(--line)/30 p-3 flex flex-col gap-2">
						<div class="flex items-center justify-between">
							<p class="text-sm text-(--ink)/70 drop-shadow-(--shade)">{pendingTeammate.email}</p>
							<button
								type="button"
								onclick={() => { pendingTeammate = null; addError = ''; }}
								class="text-(--ink)/50 hover:text-(--ink) text-sm cursor-pointer transition-colors"
							>
								Cancel
							</button>
						</div>
						<p class="text-xs text-(--ink)/50 drop-shadow-(--shade)">Please fill in the missing info for this teammate:</p>
						<div class="flex flex-col gap-2">
							{#each pendingTeammate.missing_fields as field}
								<div class="group flex flex-col gap-1">
									<Label>{fieldLabels[field] || field}</Label>
									<Input
										type={fieldTypes[field] || 'text'}
										value={(pendingTeammate as any)[field] || ''}
										oninput={(e: Event) => updatePendingField(field, (e.target as HTMLInputElement).value)}
										placeholder={fieldPlaceholders[field] || ''}
										selectedColor={eventTheme.selected}
									/>
								</div>
							{/each}
						</div>
						<Button
							onclick={savePendingTeammate}
							disabled={saving}
						>
							{#if saving}
								<p>Adding...</p>
							{:else}
								<p>Add Teammate</p>
							{/if}
						</Button>
					</div>
				{/if}

				<div class="flex flex-col gap-3">
					<p class="text-lg text-(--ink)/80 drop-shadow-(--shade)">Add a teammate</p>
					<div class="flex gap-2">
						<div class="flex-1">
							<Input
								bind:value={emailInput}
								placeholder="teammate@email.com"
								selectedColor={eventTheme.selected}
								onkeydown={handleEmailKeydown}
							/>
						</div>
						<button
							type="button"
							onclick={handleLookup}
							disabled={lookingUp || !emailInput.trim()}
							class="rounded-xl border-4 border-(--edge) px-4 py-2 text-(--on-accent) text-sm font-medium cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
							style="background-color: {eventTheme.selected};"
						>
							{lookingUp ? 'Looking up...' : 'Add'}
						</button>
					</div>
				</div>

				{#if addError}
					<p class="text-sm text-(--danger) drop-shadow-(--shade)">{addError}</p>
				{/if}
				{#if error}
					<p class="text-sm text-(--danger) drop-shadow-(--shade)">{error}</p>
				{/if}

				<button
					type="button"
					onclick={() => goto(`/${slug}/vote`)}
					class="mt-2 text-md text-(--ink)/70 underline drop-shadow-(--shade) cursor-pointer transition-colors ease-in-out duration-125 hover:text-(--accent-ink)"
				>
					Back to voting
				</button>
			</div>
		</div>
	{/if}
</div>
</main>
</ProfileGate>
{/if}
