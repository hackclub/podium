<script lang="ts">
	import { lookupTeammate, type TeammateData } from '$lib/api';
	import type { EventTheme } from '$lib/theme';
	import Input from './Input.svelte';
	import Label from './Label.svelte';

	type Props = {
		eventTheme: EventTheme;
		teammates: TeammateData[];
		onupdate: (teammates: TeammateData[]) => void;
	};

	const { eventTheme, teammates, onupdate }: Props = $props();

	type TeammateEntry = TeammateData & {
		missing_fields: string[];
		loading: boolean;
		looked_up: boolean;
		error: string;
	};

	let entries: TeammateEntry[] = $state([]);
	let emailInput = $state('');
	let lookingUp = $state(false);

	const fieldLabels: Record<string, string> = {
		first_name: 'First Name',
		last_name: 'Last Name',
		phone: 'Phone Number',
		street_1: 'Street Address',
		city: 'City',
		state: 'State / Province',
		zip_code: 'ZIP / Postal Code',
		country: 'Country',
		dob: 'Date of Birth',
	};

	const fieldPlaceholders: Record<string, string> = {
		first_name: 'Jane',
		last_name: 'Doe',
		phone: '+1 555 123 4567',
		street_1: '123 Main St',
		city: 'San Francisco',
		state: 'CA',
		zip_code: '94102',
		country: 'United States',
		dob: '',
	};

	const fieldTypes: Record<string, string> = {
		phone: 'tel',
		dob: 'date',
	};

	function emitUpdate() {
		const data: TeammateData[] = entries.map((e) => {
			const d: TeammateData = { email: e.email };
			for (const f of e.missing_fields) {
				const val = (e as any)[f];
				if (val) (d as any)[f] = val;
			}
			return d;
		});
		onupdate(data);
	}

	async function addTeammate() {
		const email = emailInput.trim().toLowerCase();
		if (!email || !email.includes('@')) return;
		if (entries.some((e) => e.email === email)) return;

		lookingUp = true;
		try {
			const result = await lookupTeammate(email);

			const entry: TeammateEntry = {
				email,
				missing_fields: result.missing_fields,
				loading: false,
				looked_up: true,
				error: '',
			};

			entries = [...entries, entry];
			emailInput = '';
			emitUpdate();
		} catch (e: any) {
			// Show error inline, don't add entry
			entries = [...entries, {
				email,
				missing_fields: [],
				loading: false,
				looked_up: false,
				error: e.message || 'Failed to look up teammate',
			}];
		} finally {
			lookingUp = false;
		}
	}

	function removeTeammate(index: number) {
		entries = entries.filter((_, i) => i !== index);
		emitUpdate();
	}

	function updateField(index: number, field: string, value: string) {
		entries = entries.map((e, i) => {
			if (i !== index) return e;
			return { ...e, [field]: value };
		});
		emitUpdate();
	}

	function handleEmailKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addTeammate();
		}
	}
</script>

<div class="flex flex-col gap-3">
	<p class="text-lg text-white/80 drop-shadow-md">Teammates (optional)</p>

	{#each entries as entry, i}
		<div class="rounded-xl border-2 border-white/30 p-3 flex flex-col gap-2">
			<div class="flex items-center justify-between">
				<p class="text-sm text-white/70 drop-shadow-md">{entry.email}</p>
				<button
					type="button"
					onclick={() => removeTeammate(i)}
					class="text-white/50 hover:text-white text-sm cursor-pointer transition-colors"
				>
					Remove
				</button>
			</div>

			{#if entry.error}
				<p class="text-sm text-red-300 drop-shadow-md">{entry.error}</p>
			{:else if entry.missing_fields.length === 0}
				<p class="text-sm text-green-300 drop-shadow-md">Profile complete</p>
			{:else}
				<p class="text-xs text-white/50 drop-shadow-md">Please fill in the missing info for this teammate:</p>
				<div class="flex flex-col gap-2">
					{#each entry.missing_fields as field}
						<div class="group flex flex-col gap-1">
							<Label selectedColor={eventTheme.selected}>{fieldLabels[field] || field}</Label>
							<Input
								type={fieldTypes[field] || 'text'}
								value={(entry as any)[field] || ''}
								oninput={(e: Event) => updateField(i, field, (e.target as HTMLInputElement).value)}
								placeholder={fieldPlaceholders[field] || ''}
								selectedColor={eventTheme.selected}
							/>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/each}

	<div class="flex gap-2">
		<div class="flex-1">
			<Input
				bind:value={emailInput}
				placeholder="teammate@email.com"
				selectedColor={eventTheme.selected}
				onkeydown={handleEmailKeydown}
			/>
		</div>
		<button
			type="button"
			onclick={addTeammate}
			disabled={lookingUp || !emailInput.trim()}
			class="rounded-xl border-4 border-white px-4 py-2 text-white text-sm font-medium cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
			style="background-color: {eventTheme.selected};"
		>
			{lookingUp ? 'Looking up...' : 'Add'}
		</button>
	</div>
</div>
