<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children, selectedColor, for: htmlFor }: { children: Snippet; selectedColor?: string; for?: string } = $props();
</script>

<label
	for={htmlFor}
	class="text-sm text-white drop-shadow-md transition-colors group-focus-within:text-[var(--selected)]"
	style="--selected: {selectedColor ?? 'white'};"
>
	{@render children()}
</label>
