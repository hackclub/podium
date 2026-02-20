<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { adminGetLeaderboard, adminUpdateProject, adminDeleteProject, type ApiLeaderboardProject } from '$lib/api';

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
	}

	function cancelEdit() {
		editingId = null;
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
									{#if project.owner_name || project.owner_email}
										<div class="text-sm text-white/50">
											<span class="text-white/30">Submitted by</span>
											<span class="text-white/70">{project.owner_name || project.owner_email}</span>
											{#if project.owner_name && project.owner_email}
												<span class="text-white/30">({project.owner_email})</span>
											{/if}
										</div>
									{/if}

									{#if project.collaborators?.length > 0}
										<div class="text-sm text-white/50">
											<span class="text-white/30">Teammates:</span>
											{#each project.collaborators as collab, ci}
												<span class="text-white/70">{collab.display_name || collab.email}</span>{#if ci < project.collaborators.length - 1}<span class="text-white/30">,</span>{/if}
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
