<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<label
	class="text-sm text-(--ink) drop-shadow-(--shade) transition-colors group-focus-within:text-(--accent-ink)"
>
	{@render children()}
</label>
