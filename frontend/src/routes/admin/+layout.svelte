<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { getCurrentUser, type ApiUser } from '$lib/api';
	import { isLoggedIn, clearToken } from '$lib/auth';
	import '../../app.css';

	const { children } = $props();

	let user: ApiUser | null = $state(null);
	let loading = $state(true);

	const isLoginPage = $derived(page.url.pathname === '/admin/login');

	let lastCheckedPath = '';

	onMount(() => {
		checkAuth();
	});

	$effect(() => {
		// Re-run auth check when navigating away from login page
		const path = page.url.pathname;
		if (path !== lastCheckedPath && !isLoginPage) {
			checkAuth();
		}
	});

	async function checkAuth() {
		lastCheckedPath = page.url.pathname;

		if (isLoginPage) {
			loading = false;
			return;
		}
		if (!isLoggedIn()) {
			goto('/admin/login');
			return;
		}
		if (user) {
			loading = false;
			return;
		}
		loading = true;
		try {
			user = await getCurrentUser();
		} catch {
			clearToken();
			goto('/admin/login');
			return;
		} finally {
			loading = false;
		}
	}

	function logout() {
		clearToken();
		goto('/admin/login');
	}

	const currentPath = $derived(page.url.pathname);
</script>

{#if isLoginPage}
	{@render children()}
{:else if loading}
	<div class="flex min-h-screen items-center justify-center bg-[#111]">
		<p class="text-white/60">Loading...</p>
	</div>
{:else}
	<div class="flex min-h-screen bg-[#111]">
		<!-- Sidebar -->
		<aside class="w-64 border-r border-white/10 p-6 flex flex-col gap-6">
			<div class="flex items-center gap-2">
				<img src="/favicon.svg" alt="Podium" class="h-6" />
				<span class="text-white text-xl font-bold">Admin</span>
			</div>

			<nav class="flex flex-col gap-1">
				<a
					href="/admin"
					class="px-3 py-2 rounded-md text-sm transition-colors {currentPath === '/admin' ? 'bg-white/10 text-white' : 'text-white/60 hover:text-white hover:bg-white/5'}"
				>
					Events
				</a>
				<a
					href="/admin/events/create"
					class="px-3 py-2 rounded-md text-sm transition-colors {currentPath === '/admin/events/create' ? 'bg-white/10 text-white' : 'text-white/60 hover:text-white hover:bg-white/5'}"
				>
					+ Create Event
				</a>
				{#if user?.is_superadmin}
					<a
						href="/admin/campfire"
						class="px-3 py-2 rounded-md text-sm transition-colors {currentPath === '/admin/campfire' ? 'bg-white/10 text-white' : 'text-white/60 hover:text-white hover:bg-white/5'}"
					>
						Campfire Job
					</a>
				{/if}
			</nav>

			<div class="mt-auto flex flex-col gap-2">
				{#if user}
					<p class="text-white/40 text-xs truncate">{user.email}</p>
				{/if}
				<button
					type="button"
					onclick={logout}
					class="text-left px-3 py-2 rounded-md text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors"
				>
					Logout
				</button>
				<a
					href="/"
					class="px-3 py-2 rounded-md text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors"
				>
					Back to Podium
				</a>
			</div>
		</aside>

		<!-- Main content -->
		<main class="flex-1 p-8 overflow-y-auto">
			{@render children()}
		</main>
	</div>
{/if}
