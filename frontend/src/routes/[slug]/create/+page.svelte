<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getContext, onMount } from 'svelte';
	import { get, type Writable } from 'svelte/store';
	import type { EventTheme } from '$lib/theme';
	import {
		createProject, attendEvent, uploadScreenshot, getMyProjects,
		type ApiEvent, type TeammateData
	} from '$lib/api';
	import { isLoggedIn } from '$lib/auth';
	import Input from '$lib/forms/Input.svelte';
	import Button from '$lib/forms/Button.svelte';
	import Label from '$lib/forms/Label.svelte';
	import Textarea from '$lib/forms/Textarea.svelte';
	import FileDropZone from '$lib/forms/FileDropZone.svelte';
	import ProfileGate from '$lib/forms/ProfileGate.svelte';
	import TeammateSection from '$lib/forms/TeammateSection.svelte';

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

	// Project form state
	let projectName = $state('');
	let playableLink = $state('');
	let repoLink = $state('');
	let description = $state('');
	let hoursSpent = $state('');
	let screenshot: File | null = $state(null);
	let teammates: TeammateData[] = $state([]);
	let submitting = $state(false);
	let error = $state('');

	const canSubmit = $derived(
		projectName.trim() !== '' && playableLink.trim() !== '' && repoLink.trim() !== '' &&
		description.trim() !== '' && String(hoursSpent).trim() !== '' && parseInt(String(hoursSpent)) > 0 &&
		screenshot !== null
	);

	onMount(async () => {
		if (!isLoggedIn()) {
			goto(`/${slug}`);
			return;
		}

		const currentEventId = get(eventIdStore);

		// Check for existing project
		if (currentEventId) {
			try {
				const ps = await getMyProjects();
				const existing = ps.find((p) => p.event_id === currentEventId);
				if (existing) goto(`/${slug}/vote`);
			} catch {}
		}
	});

	async function handleSubmit() {
		if (!canSubmit || !eventId) return;
		submitting = true;
		error = '';

		try {
			const [, image_url] = await Promise.all([
				attendEvent(eventId),
				screenshot ? uploadScreenshot(screenshot, slug) : Promise.resolve(''),
			]);

			await createProject({
				name: projectName,
				demo: playableLink,
				repo: repoLink,
				description,
				hours_spent: parseInt(hoursSpent) || 0,
				event_id: eventId,
				image_url,
				teammates: teammates.length > 0 ? teammates : undefined
			});

			goto(`/${slug}/vote`);
		} catch (e: any) {
			error = e.message || 'Failed to create project';
			submitting = false;
		}
	}
</script>

{#if eventTheme}
<ProfileGate {eventTheme}>
<main class="fixed inset-0 overflow-y-auto px-4">
<div class="flex min-h-full items-center justify-center py-12 pt-20">
	{#if eventData?.votable}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-10 drop-shadow-md text-center"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0"
				style="background-color: {eventTheme.primary};"
			></div>
			<div class="relative flex flex-col items-center gap-3">
				<p class="text-3xl text-white drop-shadow-md">Submissions are closed</p>
				<p class="text-lg text-white/70 drop-shadow-md">Voting has already started.</p>
				<button
					type="button"
					onclick={() => goto(`/${slug}/vote`)}
					class="mt-2 text-md text-white/70 underline drop-shadow-md cursor-pointer transition-colors ease-in-out duration-125 hover:text-[var(--hover-color)]"
					style="--hover-color: {eventTheme.selected};"
				>
					Go to voting
				</button>
			</div>
		</div>
	{:else}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 rounded-lg"
				style="background-color: {eventTheme.primary};"
			></div>

			<div class="relative flex flex-col gap-4">
				<p class="text-2xl text-white drop-shadow-md">Ship your project</p>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Project Name</Label>
					<Input bind:value={projectName} placeholder="Podium Pro Max Ultra" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Screenshot</Label>
					<FileDropZone onfile={(f: File) => (screenshot = f)} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Playable Link</Label>
					<Input bind:value={playableLink} placeholder="https://example.com" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Github Repo Link</Label>
					<Input bind:value={repoLink} placeholder="https://github.com/user/repo" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Project Description</Label>
					<Textarea bind:value={description} rows={4} placeholder="Introducing the new Podium Pro Max Ultra!" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Estimated Hours Spent</Label>
					<Input type="number" bind:value={hoursSpent} placeholder="10" selectedColor={eventTheme.selected} />
				</div>

				<TeammateSection
					{eventTheme}
					{teammates}
					onupdate={(t) => (teammates = t)}
				/>

				{#if error}
					<p class="text-sm text-red-300 drop-shadow-md">{error}</p>
				{/if}

				<div class="mt-2 flex flex-row gap-4 items-center">
					<Button onclick={handleSubmit} color={eventTheme.primary} selectedColor={eventTheme.selected} disabled={!canSubmit || submitting}>
						{#if submitting}
							<p>Submitting...</p>
						{:else if !canSubmit}
							<p>Fill out all fields to submit</p>
						{:else}
							<p>Submit</p>
						{/if}
					</Button>
				</div>
			</div>
		</div>
	{/if}
</div>
</main>
</ProfileGate>
{/if}
