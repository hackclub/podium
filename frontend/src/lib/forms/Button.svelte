<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	let {
		children,
		class: className = "",
		...rest
	}: HTMLButtonAttributes & { children: Snippet } = $props();
</script>

<!-- Colors come from the event skin variables set by the event layout. -->
<button
	class="shrink-0 rounded-xl bg-(--button) px-4 py-3 text-base text-(--button-ink) drop-shadow-md enabled:cursor-pointer enabled:hover:bg-(--accent) enabled:hover:text-(--button-hover-ink) disabled:cursor-not-allowed disabled:opacity-50 hover:scale-105 ease-in-out transition-all duration-125 {className}"
	{...rest}
>
	{@render children()}
</button>
