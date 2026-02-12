<script lang="ts">
	import { page } from '$app/state';
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';
	import Input from '$lib/forms/Input.svelte';
	import Button from '$lib/forms/Button.svelte';
	import Label from '$lib/forms/Label.svelte';
	import Textarea from '$lib/forms/Textarea.svelte';
	import FileDropZone from '$lib/forms/FileDropZone.svelte';
    import { fade } from 'svelte/transition';
	import { goto } from "$app/navigation";

	const slug = $derived(page.params.slug);
	const eventData = $derived(events[slug]);
	const eventTheme = $derived(eventData ? theme[eventData.theme] : null);

	let projectName = $state('');
	let playableLink = $state('');
	let repoLink = $state('');
	let description = $state('');
	let hoursSpent = $state('');
	let screenshot: File | null = $state(null);

	const canSubmit = $derived(
		projectName.trim() !== '' && playableLink.trim() !== '' && repoLink.trim() !== ''
	);

	function handleSubmit() {
		// TODO: wire up project creation
		goto(`/${slug}/vote`)
	}
</script>

<main class="fixed inset-0 flex items-center justify-center px-4 overflow-y-auto py-12 pt-20">
	{#if eventTheme}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 rounded-lg backdrop-blur-md"
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
					<Label selectedColor={eventTheme.selected}>Project Description (Pulled from Github)</Label>
					<Textarea bind:value={description} rows={4} placeholder="Introducing the new Podium Pro Max Ultra!" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Estimated Hours Spent</Label>
					<Input type="number" bind:value={hoursSpent} placeholder="10" selectedColor={eventTheme.selected} />
				</div>

				<div class="mt-2 flex flex-row gap-4 items-center">
					<Button onclick={handleSubmit} color={eventTheme.primary} selectedColor={eventTheme.selected} disabled={!canSubmit}>
						{#if !canSubmit}
							<p>Fill out all fields to submit</p>
						{:else}
							<p>Submit</p>
						{/if}
					</Button>
				</div>
			</div>
		</div>
	{/if}
</main>
