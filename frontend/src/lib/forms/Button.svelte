<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	let {
		children,
		color = '#49B6F3',
		selectedColor,
		class: className = "",
		...rest
	}: HTMLButtonAttributes & { children: Snippet; color?: string; selectedColor?: string } =
		$props();

	let hovered = $state(false);
</script>

<button
	class="shrink-0 rounded-xl px-4 py-3 text-base drop-shadow-md disabled:cursor-not-allowed disabled:opacity-50 hover:scale-105 ease-in-out transition-all duration-125 {className}"
	class:cursor-pointer={!rest.disabled}
	style="background-color: {hovered && !rest.disabled && selectedColor ? selectedColor : 'white'}; color: {hovered && !rest.disabled && selectedColor ? 'white' : color};"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	{...rest}
>
	{@render children()}
</button>
