<script lang="ts">
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';
	import { goto } from '$app/navigation';
	import { fade } from 'svelte/transition';
	import { onMount } from 'svelte';

	let searchQuery = $state('');

	let filteredEvents = $derived(
		Object.entries(events).filter(([_, data]) =>
			data.friendlyName.toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	onMount(() => {
		const backgrounds = Object.values(theme).map((t) => t.background);
		backgrounds.forEach((src) => {
			const img = new Image();
			img.src = src;
		});
	});
</script>

<div class="bg-[#111] min-h-screen relative" out:fade={{ duration: 150 }}>
	<!-- Header -->
	<div class="flex items-end gap-2 p-6 sticky">
		<img src="/favicon.svg" alt="Podium" class="h-[32px]" />
		<span class="text-white text-[32px] font-bold leading-none">Podium 2</span>
		<span class="text-[#878787] text-[16px] leading-none pb-0.5">Vote @ your event</span>
	</div>

	<!-- Content -->
	<div class="mx-auto mt-[52px] flex max-w-[589px] flex-col gap-5 px-4">
		<!-- Search Bar -->
		<label class="flex items-center gap-2 rounded-md bg-[#303030] px-4 py-2 transition-all duration-200 focus-within:ring-2 focus-within:ring-white focus-within:ring-offset-2 focus-within:ring-offset-[#111]">
			<input
				type="text"
				placeholder="Search for your event"
				bind:value={searchQuery}
				class="flex-1 bg-transparent text-[16px] text-white placeholder:text-white/40 outline-none"
			/>
			<img
				src="https://icons.hackclub.com/api/icons/white/search"
				alt="Search"
				class="size-8 opacity-60"
			/>
		</label>

		{#each filteredEvents as [slug, data], i (i)}
			{@const t = theme[data.theme]}
			{#if t}
				<div
					in:fade|global={{ duration: 100, delay: i * 15 }}
					out:fade|global={{ duration: 100 }}
					class="group flex h-[120px] w-full items-end justify-between overflow-hidden rounded-md bg-cover bg-center p-4 select-none cursor-pointer transition-all duration-200 hover:ring-2 hover:ring-white hover:ring-offset-2 hover:ring-offset-[#303030]"
					style="background-image: url({t.background});"
					onclick={() => goto(`/${slug}`)}
					onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goto(`/${slug}`); } }}
					role="button"
					tabindex="0"
					key={i}
				>
					<div class="flex items-center justify-center h-full">
						<t.logo satellite={data.satellite} />
					</div>

					<div
						class="rounded-lg bg-white px-3 py-2 text-[16px] leading-none transition-transform ease-in-out group-hover:scale-110 duration-200"
						style="color: {t.primary}; font-family: {t.font};"
					>
						Vote →
					</div>
				</div>
			{/if}
		{/each}
	</div>

	<!-- Footer -->
	<div class="fixed bottom-6 left-6">
		<span class="text-[16px] font-bold text-[#878787]">About Podium</span>
	</div>
</div>
