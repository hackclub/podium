<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';
	import { projects } from '$lib/data';

	const slug = $derived(page.params.slug);
	const eventData = $derived(events[slug]);
	const eventTheme = $derived(eventData ? theme[eventData.theme] : null);
	let hoveredId: string | null = $state(null);
</script>

<main class="flex flex-1 items-center justify-center px-4 py-12">
	{#if eventTheme}
		<div
			class="relative overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 backdrop-blur-md"
				style="background-color: {eventTheme.primary};"
			></div>

			<div class="relative flex flex-col gap-4">
				<p class="text-2xl text-white drop-shadow-md">Browse & vote on projects</p>

				<div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
					{#each projects as project}
						<button
							type="button"
							class="flex w-[280px] cursor-pointer flex-col gap-2.5 overflow-hidden rounded-xl border-4 p-3 text-left shadow-md transition-all hover:scale-[1.02]"
							style="background-color: {eventTheme.primary}; border-color: {hoveredId === project.id ? eventTheme.selected : 'white'}; color: {hoveredId === project.id ? eventTheme.selected : 'white'};"
							onmouseenter={() => (hoveredId = project.id)}
							onmouseleave={() => (hoveredId = null)}
							onclick={() => goto(`/${slug}/vote/${project.id}`)}
						>
							<div class="h-[100px] w-full rounded bg-gray-300">
								{#if project.image}
									<img
										src={project.image}
										alt={project.name}
										class="h-full w-full rounded object-cover"
									/>
								{/if}
							</div>

							<div class="flex flex-col gap-0.5 drop-shadow-md">
								<p class="text-2xl">{project.name}</p>
								<p class="text-sm opacity-80">{project.description}</p>
							</div>

							<p class="w-full text-center text-xs">Click to view</p>
						</button>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</main>
