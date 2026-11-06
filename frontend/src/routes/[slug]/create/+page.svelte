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

	const canSubmit = $derived(
		projectName.trim() !== '' && playableLink.trim() !== '' && isValidGitHubUrl &&
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
<main class="flex flex-1 flex-col px-4">
<div class="flex flex-1 items-center justify-center py-12">
	{#if eventData?.votable}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-(--edge) px-6 py-10 drop-shadow-md text-center"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 bg-(--surface)"
			></div>
			<div class="relative flex flex-col items-center gap-3">
				<p class="font-(family-name:--heading-font) text-3xl text-(--ink) drop-shadow-(--shade)">Submissions are closed</p>
				<p class="text-lg text-(--ink)/70 drop-shadow-(--shade)">Voting has already started.</p>
				<button
					type="button"
					onclick={() => goto(`/${slug}/vote`)}
					class="mt-2 text-md text-(--ink)/70 underline drop-shadow-(--shade) cursor-pointer transition-colors ease-in-out duration-125 hover:text-(--accent-ink)"
				>
					Go to voting
				</button>
			</div>
		</div>
	{:else}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-(--edge) px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 rounded-lg bg-(--surface)"
			></div>

			<div class="relative flex flex-col gap-4">
				<p class="font-(family-name:--heading-font) text-2xl text-(--ink) drop-shadow-(--shade)">Additional Information about your game</p>

				<div class="rounded-lg border border-(--line)/20 bg-(--ink)/10 px-4 py-3 text-sm text-(--ink)/80 drop-shadow-(--shade)">
					<p><strong class="text-(--ink)">Only one person per team should submit.</strong> Make sure to add all your teammates below.</p>
				</div>

				<div class="group flex flex-col gap-1">
					<Label>What are you calling your game? *</Label>
					<p class="text-xs text-(--ink)/60 drop-shadow-(--shade)">Pick a short, memorable name!</p>
					<Input bind:value={projectName} placeholder="Podium Pro Max Ultra" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label>Code URL / GitHub URL *</Label>
					<p class="text-xs text-(--ink)/60 drop-shadow-(--shade)">This must be a GitHub link!</p>
					<Input bind:value={repoLink} placeholder="https://github.com/user/repo" selectedColor={eventTheme.selected} />
					{#if repoLink.trim() !== '' && !isValidGitHubUrl}
						<p class="text-xs text-(--danger) drop-shadow-(--shade)">Please enter a valid GitHub URL (e.g. https://github.com/user/repo)</p>
					{/if}
				</div>

				<div class="group flex flex-col gap-1">
					<Label>Playable Link *</Label>
					<p class="text-xs text-(--ink)/60 drop-shadow-(--shade)">This must be a link that anyone can click on to play your game!</p>
					<Input bind:value={playableLink} placeholder="https://example.com/play" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label>Please give us a short, easy to understand description of your game *</Label>
					<Textarea bind:value={description} rows={4} placeholder="Describe your game..." selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label>Upload a thumbnail for your project: *</Label>
					<p class="text-xs text-(--ink)/60 drop-shadow-(--shade)">Upload an image or a GIF that will show up on the project gallery!</p>
					<FileDropZone onfile={(f: File) => (screenshot = f)} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label>How many hours did you (the submitter) spend on this project? *</Label>
					<p class="text-xs text-(--ink)/60 drop-shadow-(--shade)">This question won't be used to determine the prizes you win! Please provide an honest, lower bound estimate.</p>
					<Input type="number" bind:value={hoursSpent} placeholder="10" selectedColor={eventTheme.selected} />
				</div>

				<TeammateSection
					{eventTheme}
					{teammates}
					onupdate={(t) => (teammates = t)}
				/>

				{#if error}
					<p class="text-sm text-(--danger) drop-shadow-(--shade)">{error}</p>
				{/if}

				<div class="mt-2 flex flex-row gap-4 items-center">
					<Button onclick={handleSubmit} disabled={!canSubmit || submitting}>
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
