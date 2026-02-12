<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';
	import { projects } from '$lib/data';
	import Button from '$lib/forms/Button.svelte';

	const slug = $derived(page.params.slug);
	const id = $derived(page.params.id);
	const eventData = $derived(events[slug]);
	const eventTheme = $derived(eventData ? theme[eventData.theme] : null);
	const project = $derived(projects.find(p => p.id === id));
</script>

<main class="flex flex-1 items-center justify-center px-4 py-12">
	{#if eventTheme && project}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 backdrop-blur-md"
				style="background-color: {eventTheme.primary};"
			></div>

			<div class="relative flex flex-col gap-2">
				<button
					type="button"
					class="mt-1 mb-2 w-fit text-md text-white/70 underline drop-shadow-md cursor-pointer transition-colors ease-in-out duration-125 hover:text-[var(--hover-color)]"
					style="--hover-color: {eventTheme.selected};"
					onclick={() => goto(`/${slug}/vote`)}
				>
					back
				</button>

				<div class="h-40 w-full overflow-hidden rounded-xl bg-gray-300">
					{#if project.image}
						<img
							src={project.image}
							alt={project.name}
							class="h-full w-full object-cover"
						/>
					{/if}
				</div>

				<div class="flex flex-col text-white drop-shadow-md">
					<p class="text-4xl">{project.name}</p>
					<p class="text-xl text-white/80">{project.description}</p>
				</div>

				<div class="flex gap-2.5 flex-col md:flex-row">
					<a href={project.demoUrl || '#'} target="_blank" rel="noopener noreferrer" class="flex-1">
						<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full">Demo</Button>
					</a>
					<a href={project.repoUrl || '#'} target="_blank" rel="noopener noreferrer" class="flex-1">
						<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full">Repository</Button>
					</a>
					<div class="flex-1">
						<Button color={eventTheme.primary} selectedColor={eventTheme.selected} class="w-full">Vote</Button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</main>
