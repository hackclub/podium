<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { adminGetEvent, adminUpdateEvent, type ApiAdminEvent } from '$lib/api';
	import { defaultThemes } from '$lib/theme';

	const eventId = $derived(page.params.id ?? '');

	let event: ApiAdminEvent | null = $state(null);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	let themeName = $state('campfire');
	let themeBackground = $state('');
	let themeFont = $state('');
	let themePrimary = $state('');
	let themeSelected = $state('');

	onMount(async () => {
		try {
			event = await adminGetEvent(eventId);
			themeName = event.theme_name || 'campfire';
			themeBackground = event.theme_background || '';
			themeFont = event.theme_font || '';
			themePrimary = event.theme_primary || '';
			themeSelected = event.theme_selected || '';
		} catch (e: any) {
			error = e.message || 'Failed to load event';
		} finally {
			loading = false;
		}
	});

	function applyPreset() {
		const defaults = defaultThemes[themeName] || defaultThemes.campfire;
		themeBackground = defaults.background;
		themeFont = defaults.font;
		themePrimary = defaults.primary;
		themeSelected = defaults.selected;
	}

	async function handleSave() {
		saving = true;
		error = '';
		saved = false;
		try {
			event = await adminUpdateEvent(eventId, {
				theme_name: themeName,
				theme_background: themeBackground,
				theme_font: themeFont,
				theme_primary: themePrimary,
				theme_selected: themeSelected
			});
			saved = true;
			setTimeout(() => (saved = false), 2000);
		} catch (e: any) {
			error = e.message || 'Failed to save';
		} finally {
			saving = false;
		}
	}
</script>

{#if loading}
	<p class="text-white/60">Loading...</p>
{:else if event}
	<div class="max-w-2xl">
		<div class="flex items-center gap-3 mb-8">
			<button
				type="button"
				onclick={() => goto(`/admin/events/${eventId}`)}
				class="text-white/40 hover:text-white transition-colors"
			>
				← Back
			</button>
			<h1 class="text-3xl font-bold text-white">Theme Editor</h1>
		</div>

		<div class="flex flex-col gap-6">
			<!-- Preset -->
			<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10">
				<h2 class="text-lg font-medium text-white">Preset</h2>

				<div class="flex gap-3">
					<select
						bind:value={themeName}
						class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
					>
						<option value="campfire">Campfire (Satellite)</option>
						<option value="flagship">Flagship</option>
						<option value="sleepover">Sleepover</option>
					</select>
					<button
						type="button"
						onclick={applyPreset}
						class="px-4 py-2 border border-white/20 text-white/60 rounded-md text-sm hover:text-white hover:border-white/40 transition-colors"
					>
						Apply Preset Defaults
					</button>
				</div>
			</div>

			<!-- Customization -->
			<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10">
				<h2 class="text-lg font-medium text-white">Customization</h2>

				<div class="flex flex-col gap-1">
					<label for="bg" class="text-sm text-white/60">Background Image URL</label>
					<input
						id="bg"
						type="text"
						bind:value={themeBackground}
						class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
					/>
				</div>

				<div class="flex flex-col gap-1">
					<label for="font" class="text-sm text-white/60">Font Family</label>
					<input
						id="font"
						type="text"
						bind:value={themeFont}
						class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div class="flex flex-col gap-1">
						<label for="primary" class="text-sm text-white/60">Primary Color</label>
						<div class="flex items-center gap-2">
							<input type="color" bind:value={themePrimary} class="w-8 h-8 rounded cursor-pointer" />
							<input
								id="primary"
								type="text"
								bind:value={themePrimary}
								class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
							/>
						</div>
					</div>

					<div class="flex flex-col gap-1">
						<label for="selected" class="text-sm text-white/60">Accent Color</label>
						<div class="flex items-center gap-2">
							<input type="color" bind:value={themeSelected} class="w-8 h-8 rounded cursor-pointer" />
							<input
								id="selected"
								type="text"
								bind:value={themeSelected}
								class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
							/>
						</div>
					</div>
				</div>
			</div>

			<!-- Live Preview -->
			<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10">
				<h2 class="text-lg font-medium text-white">Preview</h2>

				<!-- Event Card Preview -->
				<div
					class="h-32 rounded-lg bg-cover bg-center flex items-end justify-between p-4"
					style="background-image: url({themeBackground});"
				>
					<span class="text-white text-xl font-bold drop-shadow-md" style="font-family: {themeFont};">
						{event.name}
					</span>
					<span
						class="px-3 py-1.5 rounded-lg bg-white text-sm leading-none"
						style="color: {themePrimary}; font-family: {themeFont};"
					>
						Vote →
					</span>
				</div>

				<!-- Button Preview -->
				<div class="flex gap-3">
					<div
						class="px-4 py-2 rounded-lg border-2 border-white text-white text-sm"
						style="background-color: {themePrimary}; font-family: {themeFont};"
					>
						Normal Button
					</div>
					<div
						class="px-4 py-2 rounded-lg border-2 text-sm"
						style="background-color: {themePrimary}; border-color: {themeSelected}; color: {themeSelected}; font-family: {themeFont};"
					>
						Selected Button
					</div>
				</div>
			</div>

			{#if error}
				<p class="text-red-400 text-sm">{error}</p>
			{/if}

			<div class="flex gap-3">
				<button
					type="button"
					onclick={handleSave}
					disabled={saving}
					class="px-6 py-2 bg-white text-[#111] rounded-md text-sm font-medium hover:bg-white/90 transition-colors disabled:opacity-50"
				>
					{saving ? 'Saving...' : saved ? 'Saved!' : 'Save Theme'}
				</button>
				<button
					type="button"
					onclick={() => goto(`/admin/events/${eventId}`)}
					class="px-6 py-2 border border-white/20 text-white/60 rounded-md text-sm hover:text-white hover:border-white/40 transition-colors"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
{/if}
