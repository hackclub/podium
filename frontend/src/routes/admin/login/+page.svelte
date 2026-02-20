<script lang="ts">
	import { goto } from '$app/navigation';
	import { requestAdminOtp, verifyAdminOtp } from '$lib/api';
	import { setToken, isLoggedIn } from '$lib/auth';
	import { onMount } from 'svelte';
	let email = $state('');
	let code = $state('');
	let step: 'email' | 'otp' = $state('email');
	let loading = $state(false);
	let error = $state('');

	onMount(() => {
		if (isLoggedIn()) {
			goto('/admin');
		}
	});

	async function handleRequestOtp() {
		if (!email.trim()) return;
		loading = true;
		error = '';
		try {
			await requestAdminOtp(email.trim().toLowerCase());
			step = 'otp';
		} catch (e: any) {
			// Always move to OTP step to prevent email enumeration
			step = 'otp';
		} finally {
			loading = false;
		}
	}

	async function handleVerifyOtp() {
		if (!code.trim()) return;
		loading = true;
		error = '';
		try {
			const result = await verifyAdminOtp(email.trim().toLowerCase(), code.trim());
			setToken(result.access_token);
			goto('/admin');
		} catch (e: any) {
			error = e.message || 'Invalid or expired code';
		} finally {
			loading = false;
		}
	}

	function goBack() {
		step = 'email';
		code = '';
		error = '';
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-[#111]">
	<div class="w-full max-w-sm p-8">
		<div class="flex items-center gap-2 mb-8 justify-center">
			<img src="/favicon.svg" alt="Podium" class="h-8" />
			<span class="text-white text-2xl font-bold">Admin</span>
		</div>

		{#if step === 'email'}
			<form onsubmit={(e) => { e.preventDefault(); handleRequestOtp(); }} class="flex flex-col gap-4">
				<div>
					<label for="email" class="block text-white/60 text-sm mb-1.5">Email</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						placeholder="admin@example.com"
						required
						class="w-full px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm placeholder:text-white/30"
					/>
				</div>
				{#if error}
					<p class="text-red-400 text-sm">{error}</p>
				{/if}
				<button
					type="submit"
					disabled={loading || !email.trim()}
					class="w-full py-2 bg-white text-[#111] rounded-md text-sm font-medium hover:bg-white/90 transition-colors disabled:opacity-50"
				>
					{loading ? 'Sending...' : 'Send OTP'}
				</button>
			</form>
		{:else}
			<form onsubmit={(e) => { e.preventDefault(); handleVerifyOtp(); }} class="flex flex-col gap-4">
				<p class="text-white/60 text-sm text-center">
					Enter the 6-digit code sent to <span class="text-white">{email}</span>
				</p>
				<div>
					<label for="otp" class="block text-white/60 text-sm mb-1.5">Code</label>
					<input
						id="otp"
						type="text"
						bind:value={code}
						placeholder="123456"
						maxlength={6}
						required
						autocomplete="one-time-code"
						class="w-full px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm text-center tracking-[0.3em] text-lg placeholder:text-white/30 placeholder:tracking-normal placeholder:text-sm"
					/>
				</div>
				{#if error}
					<p class="text-red-400 text-sm">{error}</p>
				{/if}
				<button
					type="submit"
					disabled={loading || code.trim().length < 6}
					class="w-full py-2 bg-white text-[#111] rounded-md text-sm font-medium hover:bg-white/90 transition-colors disabled:opacity-50"
				>
					{loading ? 'Verifying...' : 'Verify'}
				</button>
				<button
					type="button"
					onclick={goBack}
					class="text-white/40 text-sm hover:text-white transition-colors"
				>
					← Use a different email
				</button>
			</form>
		{/if}

		<div class="mt-6 text-center">
			<a href="/" class="text-white/30 text-xs hover:text-white/60 transition-colors">
				Back to Podium
			</a>
		</div>
	</div>
</div>
