<script lang="ts">
	import type { HTMLTextareaAttributes } from 'svelte/elements';

	let {
		value = $bindable(''),
		selectedColor,
		...rest
	}: HTMLTextareaAttributes & { value?: string; selectedColor?: string } = $props();

	let focused = $state(false);
</script>

<textarea
	bind:value
	onfocus={() => (focused = true)}
	onblur={() => (focused = false)}
	class="w-full rounded-xl border-4 bg-transparent p-2 text-base text-white placeholder:text-white/40 drop-shadow-md outline-none resize-none transition-colors"
	style="border-color: {focused && selectedColor ? selectedColor : 'white'};"
	{...rest}
></textarea>
