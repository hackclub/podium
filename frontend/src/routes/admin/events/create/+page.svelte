<script lang="ts">
	import { goto } from '$app/navigation';
	import { adminCreateEvent } from '$lib/api';
	import { defaultThemes } from '$lib/theme';

	let name = $state('');
	let slug = $state('');
	let description = $state('');
	let featureFlags = $state('');
	let themeName = $state('campfire');
	let themeBackground = $state(defaultThemes.campfire.background);
	let themeFont = $state(defaultThemes.campfire.font);
	let themePrimary = $state(defaultThemes.campfire.primary);
	let themeSelected = $state(defaultThemes.campfire.selected);
	let submitting = $state(false);
	let error = $state('');

	// Auto-generate slug from name
	$effect(() => {
		if (name && !slug) {
			slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
		}
	});

	// Update theme defaults when theme name changes
	function onThemeNameChange() {
		const defaults = defaultThemes[themeName] || defaultThemes.campfire;
		themeBackground = defaults.background;
		themeFont = defaults.font;
		themePrimary = defaults.primary;
		themeSelected = defaults.selected;
	}

	const canSubmit = $derived(name.trim() !== '' && slug.trim() !== '');

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;
		error = '';

		try {
			const event = await adminCreateEvent({
				name,
				slug,
				description,
				feature_flags_csv: featureFlags,
				theme_name: themeName,
				theme_background: themeBackground,
				theme_font: themeFont,
				theme_primary: themePrimary,
				theme_selected: themeSelected
			});
			goto(`/admin/events/${event.id}`);
		} catch (e: any) {
			error = e.message || 'Failed to create event';
			submitting = false;
		}
	}
</script>

<div class="max-w-2xl">
	<h1 class="text-3xl font-bold text-white mb-8">Create Event</h1>

	<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="flex flex-col gap-6">
		<!-- Basic Info -->
		<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10">
			<h2 class="text-lg font-medium text-white">Basic Info</h2>

			<div class="flex flex-col gap-1">
				<label for="name" class="text-sm text-white/60">Event Name</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					placeholder="Campfire Burlington"
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label for="slug" class="text-sm text-white/60">Slug (URL path)</label>
				<input
					id="slug"
					type="text"
					bind:value={slug}
					placeholder="campfire-burlington"
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label for="description" class="text-sm text-white/60">Description</label>
				<textarea
					id="description"
					bind:value={description}
					rows={3}
					placeholder="Event description..."
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm resize-none"
				></textarea>
			</div>

			<div class="flex flex-col gap-1">
				<label for="flags" class="text-sm text-white/60">Feature Flags (comma-separated series names)</label>
				<input
					id="flags"
					type="text"
					bind:value={featureFlags}
					placeholder="campfire-2025"
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
				/>
			</div>
		</div>

		<!-- Theme -->
		<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10">
			<h2 class="text-lg font-medium text-white">Theme</h2>

			<div class="flex flex-col gap-1">
				<label for="theme-name" class="text-sm text-white/60">Theme Preset</label>
				<select
					id="theme-name"
					bind:value={themeName}
					onchange={onThemeNameChange}
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
				>
					<option value="campfire">Campfire (Satellite)</option>
					<option value="flagship">Flagship</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label for="theme-bg" class="text-sm text-white/60">Background Image URL</label>
				<input
					id="theme-bg"
					type="text"
					bind:value={themeBackground}
					placeholder="https://..."
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label for="theme-font" class="text-sm text-white/60">Font Family</label>
				<input
					id="theme-font"
					type="text"
					bind:value={themeFont}
					class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
				/>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div class="flex flex-col gap-1">
					<label for="theme-primary" class="text-sm text-white/60">Primary Color</label>
					<div class="flex items-center gap-2">
						<input type="color" bind:value={themePrimary} class="w-8 h-8 rounded cursor-pointer" />
						<input
							id="theme-primary"
							type="text"
							bind:value={themePrimary}
							class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
						/>
					</div>
				</div>

				<div class="flex flex-col gap-1">
					<label for="theme-selected" class="text-sm text-white/60">Accent Color</label>
					<div class="flex items-center gap-2">
						<input type="color" bind:value={themeSelected} class="w-8 h-8 rounded cursor-pointer" />
						<input
							id="theme-selected"
							type="text"
							bind:value={themeSelected}
							class="flex-1 px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
						/>
					</div>
				</div>
			</div>

			<!-- Preview -->
			<div class="mt-2">
				<p class="text-sm text-white/60 mb-2">Preview</p>
				<div
					class="h-24 rounded-lg bg-cover bg-center flex items-end p-3"
					style="background-image: url({themeBackground});"
				>
					<span
						class="px-3 py-1.5 rounded-lg bg-white text-sm leading-none"
						style="color: {themePrimary}; font-family: {themeFont};"
					>
						Vote →
					</span>
				</div>
			</div>
		</div>

		{#if error}
			<p class="text-red-400 text-sm">{error}</p>
		{/if}

		<div class="flex gap-3">
			<button
				type="submit"
				disabled={!canSubmit || submitting}
				class="px-6 py-2 bg-white text-[#111] rounded-md text-sm font-medium hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{submitting ? 'Creating...' : 'Create Event'}
			</button>
			<a
				href="/admin"
				class="px-6 py-2 border border-white/20 text-white/60 rounded-md text-sm hover:text-white hover:border-white/40 transition-colors"
			>
				Cancel
			</a>
		</div>
	</form>
</div>
