<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	let {
		value = $bindable(''),
		selectedColor,
		...rest
	}: HTMLInputAttributes & { value?: string; selectedColor?: string } = $props();

	let focused = $state(false);
</script>

<input
	bind:value
	onfocus={() => (focused = true)}
	onblur={() => (focused = false)}
	class="flex-1 rounded-xl border-4 bg-transparent p-2 text-base text-white placeholder:text-white/40 drop-shadow-md outline-none transition-colors"
	style="border-color: {focused && selectedColor ? selectedColor : 'white'};"
	{...rest}
/>
