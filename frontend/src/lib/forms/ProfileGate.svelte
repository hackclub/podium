<script lang="ts">
	import { onMount } from 'svelte';
	import { getCurrentUser, updateCurrentUser, type ApiUser } from '$lib/api';
	import { isLoggedIn } from '$lib/auth';
	import type { EventTheme } from '$lib/theme';
	import Input from './Input.svelte';
	import Button from './Button.svelte';
	import Label from './Label.svelte';

	type Props = {
		eventTheme: EventTheme;
		children: import('svelte').Snippet;
	};

	const { eventTheme, children }: Props = $props();

	let needsProfile = $state(false);
	let checked = $state(false);
	let saving = $state(false);
	let error = $state('');

	let firstName = $state('');
	let lastName = $state('');
	let phone = $state('');
	let street1 = $state('');
	let street2 = $state('');
	let city = $state('');
	let addrState = $state('');
	let zipCode = $state('');
	let country = $state('');
	let dob = $state('');

	const formComplete = $derived(
		firstName.trim() !== '' && phone.trim() !== '' &&
		street1.trim() !== '' && city.trim() !== '' && addrState.trim() !== '' &&
		zipCode.trim() !== '' && country.trim() !== '' && dob.trim() !== ''
	);

	onMount(async () => {
		if (!isLoggedIn()) {
			checked = true;
			return;
		}
		try {
			const user = await getCurrentUser();
			if (!user.has_address || !user.has_dob || !user.first_name || !user.has_phone) {
				firstName = user.first_name || '';
				lastName = user.last_name || '';
				needsProfile = true;
			}
		} catch {
			// If we can't fetch the user, let them through
		}
		checked = true;
	});

	async function saveProfile() {
		saving = true;
		error = '';
		try {
			const updated = await updateCurrentUser({
				first_name: firstName,
				last_name: lastName,
				phone,
				street_1: street1,
				street_2: street2,
				city,
				state: addrState,
				zip_code: zipCode,
				country,
				dob,
			});
			if (updated.has_address && updated.has_dob && updated.first_name && updated.has_phone) {
				needsProfile = false;
			}
		} catch (e: any) {
			error = e.message || 'Failed to save profile';
		} finally {
			saving = false;
		}
	}
</script>

{#if !checked}
	<!-- Still loading user profile -->
{:else if needsProfile}
	<main class="fixed inset-0 overflow-y-auto px-4">
	<div class="flex min-h-full items-center justify-center py-12 pt-20">
		<div
			class="relative w-full max-w-lg overflow-hidden rounded-2xl border-4 border-white px-6 py-6 drop-shadow-md"
			style="font-family: {eventTheme.font};"
		>
			<div
				class="absolute inset-0 rounded-lg"
				style="background-color: {eventTheme.primary};"
			></div>

			<div class="relative flex flex-col gap-4">
				<p class="text-2xl text-white drop-shadow-md">Complete your profile</p>
				<p class="text-sm text-white/70 drop-shadow-md">We need your info before you can continue. This will not be shared with event organizers.</p>

				<div class="grid grid-cols-2 gap-4">
					<div class="group flex flex-col gap-1">
						<Label selectedColor={eventTheme.selected}>First Name</Label>
						<Input bind:value={firstName} placeholder="Jane" selectedColor={eventTheme.selected} />
					</div>
					<div class="group flex flex-col gap-1">
						<Label selectedColor={eventTheme.selected}>Last Name (optional)</Label>
						<Input bind:value={lastName} placeholder="Doe" selectedColor={eventTheme.selected} />
					</div>
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Phone Number</Label>
					<Input type="tel" bind:value={phone} placeholder="+1 555 123 4567" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Street Address</Label>
					<Input bind:value={street1} placeholder="123 Main St" selectedColor={eventTheme.selected} />
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Street Address Line 2 (optional)</Label>
					<Input bind:value={street2} placeholder="Apt 4B" selectedColor={eventTheme.selected} />
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div class="group flex flex-col gap-1">
						<Label selectedColor={eventTheme.selected}>City</Label>
						<Input bind:value={city} placeholder="San Francisco" selectedColor={eventTheme.selected} />
					</div>
					<div class="group flex flex-col gap-1">
						<Label selectedColor={eventTheme.selected}>State / Province</Label>
						<Input bind:value={addrState} placeholder="CA" selectedColor={eventTheme.selected} />
					</div>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div class="group flex flex-col gap-1">
						<Label selectedColor={eventTheme.selected}>ZIP / Postal Code</Label>
						<Input bind:value={zipCode} placeholder="94102" selectedColor={eventTheme.selected} />
					</div>
					<div class="group flex flex-col gap-1">
						<Label selectedColor={eventTheme.selected}>Country</Label>
						<Input bind:value={country} placeholder="United States" selectedColor={eventTheme.selected} />
					</div>
				</div>

				<div class="group flex flex-col gap-1">
					<Label selectedColor={eventTheme.selected}>Date of Birth</Label>
					<Input type="date" bind:value={dob} selectedColor={eventTheme.selected} />
				</div>

				{#if error}
					<p class="text-sm text-red-300 drop-shadow-md">{error}</p>
				{/if}

				<div class="mt-2 flex flex-row gap-4 items-center">
					<Button onclick={saveProfile} color={eventTheme.primary} selectedColor={eventTheme.selected} disabled={!formComplete || saving}>
						{#if saving}
							<p>Saving...</p>
						{:else if !formComplete}
							<p>Fill out all required fields</p>
						{:else}
							<p>Continue</p>
						{/if}
					</Button>
				</div>
			</div>
		</div>
	</div>
	</main>
{:else}
	{@render children()}
{/if}
