<script lang="ts">
	import { page } from '$app/state';
	import { theme } from '$lib/theme';
	import { events } from '$lib/data';
	import Input from '$lib/forms/Input.svelte';
	import Button from '$lib/forms/Button.svelte';
    import { goto } from '$app/navigation';

	let email = $state('');

	const slug = $derived(page.params.slug);
	const eventData = $derived(events[slug]);
	const eventTheme = $derived(eventData ? theme[eventData.theme] : null);

	const canSubmit = $derived(email.trim() !== '');

	function handleSubmit() {
		// TODO: wire up magic link auth

        goto(`/${slug}/create`)
	}
</script>

<main class="fixed inset-0 flex items-center justify-center px-4">
	{#if eventTheme}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-lg border-4 border-white p-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 rounded-lg"
				style="background-color: {eventTheme.primary};"
			></div>

			<div class="relative flex flex-col gap-2">
                <div>
                    <p class="text-2xl text-white drop-shadow-md">
                        Sign in to create your project and vote
                    </p>
                    <p class="text-lg text-white/70 drop-shadow-md">We'll send you an email</p>
                </div>

				<div class="mt-2 flex gap-2.5">
					<Input type="email" bind:value={email} placeholder="example@email.com" selectedColor={eventTheme.selected} />
					<Button onclick={handleSubmit} color={eventTheme.primary} selectedColor={eventTheme.selected} disabled={!canSubmit}>
						Login / Sign Up
					</Button>
				</div>

				<button
                    type="button"
					onclick={() => history.back()}
					class="mt-1 w-fit text-md text-white/70 underline drop-shadow-md cursor-pointer"
				>
					back
				</button>
			</div>
		</div>
	{/if}
</main>
