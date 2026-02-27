<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		adminGetPlatformSettings,
		adminUpdatePlatformSettings,
		type PlatformSettings,
		type ApiUser,
	} from '$lib/api';
	import { toast } from 'svelte-sonner';

	const getAdminUser = getContext<() => ApiUser | null>('adminUser');

	let settings: PlatformSettings | null = $state(null);
	let loading = $state(true);
	let saving = $state(false);

	onMount(async () => {
		const user = getAdminUser();
		if (!user?.is_superadmin) {
			goto('/admin');
			return;
		}
		try {
			settings = await adminGetPlatformSettings();
		} catch (e: any) {
			toast.error(e.message || 'Failed to load platform settings');
		} finally {
			loading = false;
		}
	});

	async function toggle(field: keyof PlatformSettings) {
		if (!settings || saving) return;
		saving = true;
		try {
			settings = await adminUpdatePlatformSettings({ [field]: !settings[field] });
			const label = field.replace(/_/g, ' ');
			toast.success(`${label} ${settings[field] ? 'enabled' : 'disabled'}`);
		} catch (e: any) {
			toast.error(e.message || 'Failed to update setting');
		} finally {
			saving = false;
		}
	}
</script>

<div class="max-w-2xl">
	<h1 class="text-2xl font-bold text-white mb-6">Platform Settings</h1>

	{#if loading}
		<p class="text-white/60">Loading...</p>
	{:else if settings}
		<div class="flex flex-col gap-4 p-6 rounded-lg bg-white/5 border border-white/10">
			<h2 class="text-lg font-medium text-white">Validation</h2>
			<p class="text-sm text-white/40">
				Control whether external URL validation runs during project creation.
				Format checks (URL pattern matching) always run regardless of these settings.
			</p>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<span class="text-sm text-white/80">GitHub Validation</span>
					<p class="text-xs text-white/40 mt-0.5">Check that GitHub repos are publicly accessible</p>
				</div>
				<input
					type="checkbox"
					checked={settings.github_validation_enabled}
					onchange={() => toggle('github_validation_enabled')}
					disabled={saving}
					class="w-5 h-5 rounded cursor-pointer"
				/>
			</label>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<span class="text-sm text-white/80">Itch.io Validation</span>
					<p class="text-xs text-white/40 mt-0.5">Check that itch.io games are browser-playable</p>
				</div>
				<input
					type="checkbox"
					checked={settings.itch_validation_enabled}
					onchange={() => toggle('itch_validation_enabled')}
					disabled={saving}
					class="w-5 h-5 rounded cursor-pointer"
				/>
			</label>
		</div>
	{/if}
</div>
