<script lang="ts">
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';
    import { goto } from '$app/navigation';
</script>

<div class="bg-[#111] min-h-screen relative">
	<!-- Header -->
	<div class="flex items-end gap-2 p-6 sticky">
		<span class="text-white text-[32px] font-bold leading-none">Podium 2</span>
		<span class="text-[#878787] text-[16px] leading-none pb-0.5">Vote @ your event</span>
	</div>

	<!-- Content -->
	<div class="mx-auto mt-[52px] flex max-w-[589px] flex-col gap-5 px-4">
		<!-- Search Bar -->
		<label class="flex items-center gap-2 rounded-2xl bg-[#303030] px-4 py-2">
			<input
				type="text"
				placeholder="Search for your event"
				class="flex-1 bg-transparent text-[16px] text-white placeholder:text-white/40 outline-none"
			/>
			<img
				src="https://icons.hackclub.com/api/icons/white/search"
				alt="Search"
				class="size-8 opacity-60"
			/>
		</label>

		{#each Object.entries(events) as [slug, data]}
			{@const t = theme[data.theme]}
			{#if t}
				<div
					class="flex h-[120px] w-full items-end justify-between overflow-hidden rounded-md bg-cover bg-center p-4 select-none cursor-pointer transition-all duration-200 hover:ring-2 hover:ring-white hover:ring-offset-2 hover:ring-offset-[#303030]"
					style="background-image: url({t.background});"
					onclick={() => goto(`/${slug}`)}
					onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goto(`/${slug}`); } }}
					role="button"
					tabindex="0"
				>
					<div class="mb-auto mt-4">
						<svelte:component this={t.logo} satellite={data.satellite} />
					</div>

					<div
						class="rounded-lg bg-white px-3 py-2 text-[16px] leading-none"
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
