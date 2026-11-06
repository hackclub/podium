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
	class="w-full min-w-0 flex-1 rounded-xl border-4 bg-(--field) p-2 text-base text-(--ink) placeholder:text-(--ink)/40 drop-shadow-(--shade) outline-none transition-colors"
	style="border-color: {focused && selectedColor ? selectedColor : 'var(--line)'};"
	{...rest}
/>
