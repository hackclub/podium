<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { adminGetLeaderboard, adminUpdateProject, adminDeleteProject, adminAddCollaborator, adminRemoveCollaborator, lookupTeammate, type ApiLeaderboardProject, type TeammateData } from '$lib/api';

	const eventId = $derived(page.params.id ?? '');

	let projects: ApiLeaderboardProject[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let expandedId: string | null = $state(null);
	let editingId: string | null = $state(null);
	let editName = $state('');
	let editDescription = $state('');
	let editDemo = $state('');
	let editRepo = $state('');
	let saving = $state(false);
	let deletingId: string | null = $state(null);

	// Teammate editing state
	let editCollaborators: { user_id: string; display_name: string; email?: string }[] = $state([]);
	let teammateEmail = $state('');
	let lookingUpTeammate = $state(false);
	let teammateError = $state('');
	let pendingTeammates: (TeammateData & { missing_fields: string[]; error: string })[] = $state([]);

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

	onMount(async () => {
		await loadProjects();
	});

	async function loadProjects() {
		loading = true;
		try {
			projects = await adminGetLeaderboard(eventId);
		} catch (e: any) {
			error = e.message || 'Failed to load projects';
		} finally {
			loading = false;
		}
	}

	function startEdit(project: ApiLeaderboardProject) {
		editingId = project.id;
		editName = project.name;
		editDescription = project.description;
		editDemo = project.demo;
		editRepo = project.repo;
		editCollaborators = [...(project.collaborators || [])];
		pendingTeammates = [];
		teammateEmail = '';
		teammateError = '';
	}

	function cancelEdit() {
		editingId = null;
		pendingTeammates = [];
		teammateError = '';
	}

	async function addTeammateByEmail() {
		const email = teammateEmail.trim().toLowerCase();
		if (!email || !email.includes('@')) return;
		teammateError = '';

		if (pendingTeammates.some((t) => t.email === email)) {
			teammateError = 'Already added';
			return;
		}

		lookingUpTeammate = true;
		try {
			const result = await lookupTeammate(email);
			if (result.missing_fields.length === 0) {
				const collab = await adminAddCollaborator(editingId!, { email });
				editCollaborators = [...editCollaborators, collab];
				teammateEmail = '';
			} else {
				pendingTeammates = [...pendingTeammates, { email, missing_fields: result.missing_fields, error: '' }];
				teammateEmail = '';
			}
		} catch (e: any) {
			teammateError = e.message || 'Failed to look up teammate';
		} finally {
			lookingUpTeammate = false;
		}
	}

	async function savePendingTeammate(index: number) {
		const mate = pendingTeammates[index];
		try {
			const data: TeammateData = { email: mate.email };
			for (const f of mate.missing_fields) {
				const val = (mate as any)[f];
				if (val) (data as any)[f] = val;
			}
			const collab = await adminAddCollaborator(editingId!, data);
			editCollaborators = [...editCollaborators, collab];
			pendingTeammates = pendingTeammates.filter((_, i) => i !== index);
		} catch (e: any) {
			pendingTeammates = pendingTeammates.map((t, i) =>
				i === index ? { ...t, error: e.message || 'Failed to add' } : t
			);
		}
	}

	function removePendingTeammate(index: number) {
		pendingTeammates = pendingTeammates.filter((_, i) => i !== index);
	}

	async function removeCollaborator(userId: string) {
		if (!editingId) return;
		try {
			await adminRemoveCollaborator(editingId, userId);
			editCollaborators = editCollaborators.filter((c) => c.user_id !== userId);
		} catch (e: any) {
			error = e.message || 'Failed to remove collaborator';
		}
	}

	function updatePendingField(index: number, field: string, value: string) {
		pendingTeammates = pendingTeammates.map((t, i) =>
			i === index ? { ...t, [field]: value } : t
		);
	}

	async function saveEdit() {
		if (!editingId) return;
		saving = true;
		try {
			await adminUpdateProject(editingId, {
				name: editName,
				description: editDescription,
				demo: editDemo,
				repo: editRepo
			});
			editingId = null;
			await loadProjects();
		} catch (e: any) {
			error = e.message || 'Failed to save';
		} finally {
			saving = false;
		}
	}

	async function handleDelete(projectId: string) {
		if (deletingId !== projectId) {
			deletingId = projectId;
			return;
		}
		try {
			await adminDeleteProject(projectId);
			deletingId = null;
			await loadProjects();
		} catch (e: any) {
			error = e.message || 'Failed to delete';
		}
	}
</script>

<div class="max-w-4xl">
	<div class="flex items-center gap-3 mb-8">
		<button
			type="button"
			onclick={() => goto(`/admin/events/${eventId}`)}
			class="text-white/40 hover:text-white transition-colors"
		>
			← Back
		</button>
		<h1 class="text-3xl font-bold text-white">Projects</h1>
		<span class="text-white/40 text-sm">({projects.length})</span>
	</div>

	{#if loading}
		<p class="text-white/60">Loading...</p>
	{:else if error && projects.length === 0}
		<p class="text-red-400">{error}</p>
	{:else if projects.length === 0}
		<p class="text-white/60 text-center py-12">No projects yet</p>
	{:else}
		{#if error}
			<p class="text-red-400 text-sm mb-4">{error}</p>
		{/if}

		<div class="flex flex-col gap-3">
			{#each projects as project, i}
				{@const isExpanded = expandedId === project.id}
				<div class="rounded-lg bg-white/5 border border-white/10 overflow-hidden">
					{#if editingId === project.id}
						<!-- Edit mode -->
						<div class="flex flex-col gap-3 p-4">
							<input
								type="text"
								bind:value={editName}
								class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
								placeholder="Project name"
							/>
							<textarea
								bind:value={editDescription}
								rows={2}
								class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm resize-none"
								placeholder="Description"
							></textarea>
							<input
								type="text"
								bind:value={editDemo}
								class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
								placeholder="Demo URL"
							/>
							<input
								type="text"
								bind:value={editRepo}
								class="px-3 py-2 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-sm"
								placeholder="Repo URL"
							/>

							<!-- Teammates section -->
							<div class="border border-white/10 rounded-md p-3 flex flex-col gap-2">
								<p class="text-white/50 text-xs font-medium uppercase tracking-wide">Teammates</p>

								{#if editCollaborators.length > 0}
									<div class="flex flex-col gap-1.5">
										{#each editCollaborators as collab}
											<div class="flex items-center justify-between bg-white/5 rounded px-2.5 py-1.5">
												<span class="text-white/70 text-sm">{collab.display_name}</span>
												<button
													type="button"
													onclick={() => removeCollaborator(collab.user_id)}
													class="text-red-400/60 hover:text-red-400 text-xs transition-colors"
												>
													Remove
												</button>
											</div>
										{/each}
									</div>
								{:else if pendingTeammates.length === 0}
									<p class="text-white/30 text-xs">No teammates</p>
								{/if}

								{#each pendingTeammates as mate, mi}
									<div class="bg-white/5 rounded p-2.5 flex flex-col gap-2">
										<div class="flex items-center justify-between">
											<span class="text-white/70 text-sm">{mate.email}</span>
											<button
												type="button"
												onclick={() => removePendingTeammate(mi)}
												class="text-white/40 hover:text-white text-xs transition-colors"
											>
												Cancel
											</button>
										</div>
										{#if mate.error}
											<p class="text-red-400 text-xs">{mate.error}</p>
										{/if}
										<p class="text-white/40 text-xs">Fill in missing info:</p>
										{#each mate.missing_fields as field}
											<div class="flex flex-col gap-0.5">
												<label class="text-white/40 text-xs">{fieldLabels[field] || field}</label>
												<input
													type={field === 'dob' ? 'date' : field === 'phone' ? 'tel' : 'text'}
													value={(mate as any)[field] || ''}
													oninput={(e) => updatePendingField(mi, field, (e.target as HTMLInputElement).value)}
													class="px-2 py-1 rounded bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-xs"
												/>
											</div>
										{/each}
										<button
											type="button"
											onclick={() => savePendingTeammate(mi)}
											class="px-2 py-1 bg-white/10 text-white/70 rounded text-xs hover:bg-white/20 transition-colors self-start"
										>
											Add teammate
										</button>
									</div>
								{/each}

								{#if teammateError}
									<p class="text-red-400 text-xs">{teammateError}</p>
								{/if}

								<div class="flex gap-2">
									<input
										type="text"
										bind:value={teammateEmail}
										placeholder="teammate@email.com"
										class="flex-1 px-2 py-1.5 rounded-md bg-white/10 text-white border border-white/20 outline-none focus:border-white/40 text-xs"
										onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTeammateByEmail(); } }}
									/>
									<button
										type="button"
										onclick={addTeammateByEmail}
										disabled={lookingUpTeammate || !teammateEmail.trim()}
										class="px-3 py-1.5 bg-white/10 text-white/70 rounded-md text-xs hover:bg-white/20 transition-colors disabled:opacity-40"
									>
										{lookingUpTeammate ? 'Looking up...' : 'Add'}
									</button>
								</div>
							</div>

							<div class="flex gap-2">
								<button
									type="button"
									onclick={saveEdit}
									disabled={saving}
									class="px-3 py-1.5 bg-white text-[#111] rounded-md text-xs font-medium hover:bg-white/90 transition-colors disabled:opacity-50"
								>
									{saving ? 'Saving...' : 'Save'}
								</button>
								<button
									type="button"
									onclick={cancelEdit}
									class="px-3 py-1.5 border border-white/20 text-white/60 rounded-md text-xs hover:text-white transition-colors"
								>
									Cancel
								</button>
							</div>
						</div>
					{:else}
						<!-- View mode -->
						<button
							type="button"
							class="flex items-center justify-between w-full p-4 text-left hover:bg-white/5 transition-colors"
							onclick={() => expandedId = isExpanded ? null : project.id}
						>
							<div class="flex items-center gap-4 min-w-0">
								<span class="text-white/30 text-sm w-6 text-right shrink-0">#{i + 1}</span>
								{#if project.image_url}
									<img src={project.image_url} alt="" class="w-10 h-10 rounded object-cover shrink-0" />
								{:else}
									<div class="w-10 h-10 rounded bg-white/10 shrink-0"></div>
								{/if}
								<div class="min-w-0">
									<p class="text-white font-medium">{project.name}</p>
									<p class="text-white/40 text-xs truncate max-w-md">{project.description}</p>
								</div>
							</div>

							<div class="flex items-center gap-4 shrink-0">
								<span class="text-white/60 text-sm">{project.vote_count} votes</span>
								<span class="text-white/30 text-sm transition-transform {isExpanded ? 'rotate-180' : ''}">▼</span>
							</div>
						</button>

						{#if isExpanded}
							<div class="px-4 pb-4 ml-10 border-t border-white/5 pt-3 flex flex-col gap-3">
								{#if project.image_url}
									<img src={project.image_url} alt={project.name} class="w-full max-w-md rounded-lg object-cover" />
								{/if}

								<p class="text-white/60 text-sm">{project.description}</p>

								<div class="flex flex-col gap-1.5">
									{#if project.owner_name}
										<div class="text-sm text-white/50">
											<span class="text-white/30">Submitted by</span>
											<span class="text-white/70">{project.owner_name}</span>
										</div>
									{/if}

									{#if project.collaborators?.length > 0}
										<div class="text-sm text-white/50">
											<span class="text-white/30">Teammates:</span>
											{#each project.collaborators as collab, ci}
												<span class="text-white/70">{collab.display_name}</span>{#if ci < project.collaborators.length - 1}<span class="text-white/30">,</span>{/if}
											{/each}
										</div>
									{/if}

									{#if project.hours_spent}
										<div class="text-sm text-white/50">
											<span class="text-white/30">Hours spent:</span>
											<span class="text-white/70">{project.hours_spent}</span>
										</div>
									{/if}
								</div>

								{#if project.repo || project.demo}
									<div class="flex gap-3 flex-wrap">
										{#if project.repo}
											<a href={project.repo} target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 text-sm">
												Repo ↗
											</a>
										{/if}
										{#if project.demo}
											<a href={project.demo} target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 text-sm">
												Demo ↗
											</a>
										{/if}
									</div>
								{/if}

								<div class="flex gap-2 mt-1">
									<button
										type="button"
										onclick={(e) => { e.stopPropagation(); startEdit(project); }}
										class="px-3 py-1.5 border border-white/20 text-white/60 rounded-md text-xs hover:text-white hover:border-white/40 transition-colors"
									>
										Edit
									</button>
									<button
										type="button"
										onclick={(e) => { e.stopPropagation(); handleDelete(project.id); }}
										class="px-3 py-1.5 border border-red-500/30 text-red-400/60 rounded-md text-xs hover:text-red-400 hover:border-red-500/50 transition-colors"
									>
										{deletingId === project.id ? 'Confirm?' : 'Delete'}
									</button>
								</div>
							</div>
						{/if}
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
