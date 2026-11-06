<script lang="ts">
	let { satellite = '', height = 64 }: { satellite?: string; height?: number } = $props();

	// Event names are "Haven <City>"; the logo already says Haven.
	const city = $derived(satellite.replace(/^haven\s*/i, ''));
</script>

<div class="flex flex-col items-center gap-1">
	<img src="/haven-logo.webp" alt="Haven" style="height: {height * 1.5}px;" class="w-auto object-contain" />
	{#if city}
		<p
			class="max-w-[20ch] text-balance text-center font-(family-name:--heading-font) text-4xl leading-none tracking-tight text-white sm:text-5xl"
			style="text-shadow: 0 0 10px #ffd059, 0 0 4px #ed5615;"
		>
			{city}
		</p>
	{/if}
</div>
