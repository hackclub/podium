<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children, selectedColor }: { children: Snippet; selectedColor?: string } = $props();
</script>

<label
	class="text-sm text-white drop-shadow-md transition-colors group-focus-within:text-[var(--selected)]"
	style="--selected: {selectedColor ?? 'white'};"
>
	{@render children()}
</label>
