<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getContext, onMount } from 'svelte';
	import { get, type Writable } from 'svelte/store';
	import type { EventTheme } from '$lib/theme';
	import type { ApiEvent } from '$lib/api';
	import { requestLogin, verifyToken, userExists, createUser, getCurrentUser, getMyProjects } from '$lib/api';
	import { setToken, isLoggedIn } from '$lib/auth';
	import Input from '$lib/forms/Input.svelte';
	import Button from '$lib/forms/Button.svelte';

	const eventStore = getContext<Writable<ApiEvent | null>>('event');
	const eventThemeStore = getContext<Writable<EventTheme | null>>('eventTheme');
	const eventIdStore = getContext<Writable<string | null>>('eventId');

	let eventTheme: EventTheme | null = $state(null);

	$effect(() => {
		const unsub = eventThemeStore.subscribe((v) => (eventTheme = v));
		return () => unsub();
	});

	const slug = $derived(page.params.slug);

	let email = $state('');
	let firstName = $state('');
	let showNameFields = $state(false);
	let status = $state<'idle' | 'loading' | 'sent' | 'verifying' | 'error'>('idle');
	let errorMsg = $state('');

	const canSubmit = $derived(
		email.trim() !== '' && (!showNameFields || firstName.trim() !== '')
	);

	onMount(async () => {
		// Check for token verification from magic link
		const urlParams = new URLSearchParams(window.location.search);
		const token = urlParams.get('token');
		if (token) {
			status = 'verifying';
			try {
				const result = await verifyToken(token);
				setToken(result.access_token);
				const redirectSlug = urlParams.get('redirect') || slug;
				window.history.replaceState({}, '', `/${redirectSlug}`);
				// Determine whether to go to create or vote
				let destination = 'create';
				try {
					const currentEventId = await new Promise<string | null>((resolve) => {
						const id = get(eventIdStore);
						if (id !== null) { resolve(id); return; }
						const unsub = eventIdStore.subscribe((v) => {
							if (v !== null) { unsub(); resolve(v); }
						});
						setTimeout(() => { unsub(); resolve(null); }, 3000);
					});
					if (currentEventId) {
						const myProjects = await getMyProjects();
						const existing = myProjects.find((p) => p.event_id === currentEventId);
						if (existing) destination = 'vote';
					}
				} catch { /* non-fatal */ }
				goto(`/${redirectSlug}/${destination}`);
				return;
			} catch (e: any) {
				status = 'error';
				errorMsg = e.message || 'Invalid or expired token';
				return;
			}
		}

		// If already logged in, skip ahead — go directly to vote if they already
		// have a project, otherwise go to create.
		if (isLoggedIn()) {
			try {
				await getCurrentUser();

				// Wait for the layout to finish loading the event (eventIdStore is
				// populated asynchronously by the parent layout).
				const currentEventId = await new Promise<string | null>((resolve) => {
					const id = get(eventIdStore);
					if (id !== null) { resolve(id); return; }
					const unsub = eventIdStore.subscribe((v) => {
						if (v !== null) { unsub(); resolve(v); }
					});
					// Give up after 3 seconds and resolve null
					setTimeout(() => { unsub(); resolve(null); }, 3000);
				});

				if (currentEventId) {
					try {
						const myProjects = await getMyProjects();
						const existing = myProjects.find((p) => p.event_id === currentEventId);
						goto(`/${slug}/${existing ? 'vote' : 'create'}`);
					} catch {
						goto(`/${slug}/create`);
					}
				} else {
					goto(`/${slug}/create`);
				}
			} catch {
				// Token invalid, stay on login
			}
		}
	});

	async function handleSubmit() {
		if (!canSubmit) return;
		status = 'loading';
		errorMsg = '';

		try {
			const { exists } = await userExists(email);

			if (!exists && !showNameFields) {
				showNameFields = true;
				status = 'idle';
				return;
			}

			if (!exists) {
				await createUser({ email, first_name: firstName });
			}

			await requestLogin(email, slug);
			status = 'sent';
		} catch (e: any) {
			status = 'error';
			errorMsg = e.message || 'Something went wrong';
		}
	}
</script>

<main class="flex flex-1 flex-col px-4">
<div class="flex flex-1 items-center justify-center py-12">
	{#if eventTheme}
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-(--edge) p-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 rounded-lg bg-(--surface)"
			></div>

			<div class="relative flex flex-col gap-2">
				{#if status === 'sent'}
					<div>
						<p class="font-(family-name:--heading-font) text-2xl text-(--ink) drop-shadow-(--shade)">Check your email!</p>
						<p class="text-lg text-(--ink)/70 drop-shadow-(--shade)">
							We sent a magic link to {email}
						</p>
					</div>
				{:else if status === 'verifying'}
					<p class="font-(family-name:--heading-font) text-2xl text-(--ink) drop-shadow-(--shade)">Verifying...</p>
				{:else}
					<div>
						<p class="font-(family-name:--heading-font) text-2xl text-(--ink) drop-shadow-(--shade)">
							Sign in to create your project and vote
						</p>
						<p class="text-lg text-(--ink)/70 drop-shadow-(--shade)">We'll send you an email</p>
					</div>

					{#if showNameFields}
						<div class="mt-2 flex gap-2.5">
							<Input bind:value={firstName} placeholder="First name" selectedColor={eventTheme.selected} />
						</div>
					{/if}

					<div class="mt-2 flex gap-2.5">
						<Input type="email" bind:value={email} placeholder="example@email.com" selectedColor={eventTheme.selected} />
						<Button
							onclick={handleSubmit}
							disabled={!canSubmit || status === 'loading'}
						>
							{status === 'loading' ? 'Sending...' : showNameFields ? 'Create & Login' : 'Login / Sign Up'}
						</Button>
					</div>

					{#if status === 'error'}
						<p class="text-sm text-(--danger) drop-shadow-(--shade)">{errorMsg}</p>
					{/if}
				{/if}

				<button
					type="button"
					onclick={() => goto('/')}
					class="mt-1 w-fit text-md text-(--ink)/70 underline drop-shadow-(--shade) cursor-pointer transition-colors ease-in-out duration-125 hover:text-(--accent-ink)"
				>
					back
				</button>
			</div>
		</div>
	{/if}
</div>
</main>
