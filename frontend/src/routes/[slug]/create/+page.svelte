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

	const isValidGitHubUrl = $derived(
		/^https?:\/\/github\.com\/[a-zA-Z0-9\-_.]+\/[a-zA-Z0-9\-_.]+\/?$/.test(repoLink.trim())
	);

	const isValidItchUrl = $derived(
		/^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/i.test(playableLink.trim())
	);

	const canSubmit = $derived(
		projectName.trim() !== '' && isValidItchUrl && isValidGitHubUrl &&
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
				<p class="text-2xl text-white drop-shadow-md">Additional Information about your game</p>

				<div class="rounded-lg border border-white/20 bg-white/10 px-4 py-3 text-sm text-white/80 drop-shadow-md">
					<p><strong class="text-white">Only one person per team should submit.</strong> Make sure to add all your teammates below.</p>
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>What are you calling your game? *</Label>
					<p class="text-xs text-white/60 drop-shadow-md">Pick a short, memorable name!</p>
					<Input bind:value={projectName} placeholder="Podium Pro Max Ultra" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Code URL / GitHub URL *</Label>
					<p class="text-xs text-white/60 drop-shadow-md">This must be a GitHub link!</p>
					<Input bind:value={repoLink} placeholder="https://github.com/user/repo" selectedColor={eventTheme.selected} />
					{#if repoLink.trim() !== '' && !isValidGitHubUrl}
						<p class="text-xs text-red-300 drop-shadow-md">Please enter a valid GitHub URL (e.g. https://github.com/user/repo)</p>
					{/if}
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Itch.io URL *</Label>
					<p class="text-xs text-white/60 drop-shadow-md">This must be a link on itch.io that anyone can click on to play your game!</p>
					<Input bind:value={playableLink} placeholder="https://username.itch.io/game" selectedColor={eventTheme.selected} />
					{#if playableLink.trim() !== '' && !isValidItchUrl}
						<p class="text-xs text-red-300 drop-shadow-md">Please enter a valid itch.io URL (e.g. https://username.itch.io/game)</p>
					{/if}
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Please give us a short, easy to understand description of your game *</Label>
					<Textarea bind:value={description} rows={4} placeholder="Describe your game..." selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Upload a thumbnail for your project: *</Label>
					<p class="text-xs text-white/60 drop-shadow-md">Upload an image or a GIF that will show up on the project gallery!</p>
					<FileDropZone onfile={(f: File) => (screenshot = f)} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>How many hours did you (the submitter) spend on this project? *</Label>
					<p class="text-xs text-white/60 drop-shadow-md">This question won't be used to determine the prizes you win! Please provide an honest, lower bound estimate.</p>
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
