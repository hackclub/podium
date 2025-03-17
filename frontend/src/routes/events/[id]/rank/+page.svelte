<svelte:options runes />

<script lang="ts">
  import { toast } from "svelte-sonner";
  import { EventsService } from "$lib/client/sdk.gen";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { handleError } from "$lib/misc.js";
  import Icon from "@iconify/svelte";
  import type { ComponentType } from "svelte";
  import type { PageData } from "./$types";

  let { data } = $props();
  let { event, projects } = data;
  let selectedProjects: string[] = $state([]);
  let toSelect = projects.length >= 20 ? 3 : 2;
  let isSubmitting = $state(false);
  
  // Get the selected project details for the summary
  let selectedProjectDetails = $derived(projects.filter(project => 
    selectedProjects.includes(project.id)
  ));

  function toggleProjectSelection(projectId: string) {
    if (selectedProjects.includes(projectId)) {
      // If the project is already selected, remove it from the list
      selectedProjects = selectedProjects.filter((id) => id !== projectId);
    } else {
      if (selectedProjects.length < toSelect) {
        // If the project is not selected and the limit is not reached, add it to the list
        selectedProjects = [...selectedProjects, projectId];
      } else {
        toast(`You can only select ${toSelect} projects`);
      }
    }
  }

  async function submitVote() {
    if (
      selectedProjects.length < 2 ||
      (projects.length >= 20 && selectedProjects.length < 3)
    ) {
      toast(`Please select ${toSelect} projects`);
      return;
    }
    
    isSubmitting = true;
    try {
      await EventsService.voteEventsVotePost({
        body: { event_id: event.id, projects: selectedProjects },
        throwOnError: true,
      });
      toast("Vote submitted successfully");
      // Clear selection after successful submission
      selectedProjects = [];
    } catch (err) {
      handleError(err);
    } finally {
      isSubmitting = false;
    }
  }
</script>

<div class="max-w-6xl mx-auto py-8 px-6">
  <header class="mb-8 text-center">
    <h1 class="text-3xl font-medium mb-3">Rank Projects</h1>
  </header>

  <!-- Instructions Card -->
  <div class="bg-info text-info-content p-6 rounded-lg mb-8 max-w-2xl mx-auto">
    <div class="flex items-start">
      <Icon icon="mdi:information-outline" style="font-size: 24px;" class="mr-3 mt-1 flex-shrink-0" />
      <div>
        <h2 class="text-xl font-medium mb-2">How to Vote</h2>
        <ol class="list-decimal list-inside space-y-2 ml-2">
          <li>Browse through all the projects below</li>
          <li>Select your top {toSelect} favorite projects by clicking on them</li>
          <li>Submit your vote when you're ready</li>
        </ol>
        <p class="mt-4 text-sm">Note: You must select exactly {toSelect} projects to submit your vote.</p>
      </div>
    </div>
  </div>

  <!-- Projects Grid with Voting Controls -->
  <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
    <h2 class="text-2xl font-medium">Available Projects</h2>
    <div class="flex items-center gap-3">
      <div class="badge badge-neutral">{projects.length} Projects</div>
      <div class="badge {selectedProjects.length === toSelect ? 'badge-success' : 'badge-info'}">
        {selectedProjects.length}/{toSelect} Selected
      </div>
    </div>
  </div>
  
  <!-- Selected Projects Summary (Compact) -->
  {#if selectedProjects.length > 0}
    <div class="bg-neutral p-4 rounded-lg mb-6 border border-accent/20">
      <div class="flex flex-wrap gap-2">
        {#each selectedProjectDetails as project}
          <div class="badge badge-accent gap-1 p-3">
            <span>{project.name}</span>
            <button 
              class="btn btn-xs btn-circle btn-ghost" 
              onclick={() => toggleProjectSelection(project.id)}
              aria-label="Remove selection"
            >
              <Icon icon="mdi:close" style="font-size: 14px;" />
            </button>
          </div>
        {/each}
      </div>
    </div>
  {/if}
  
  {#if projects.length === 0}
    <div class="bg-base-200 rounded-lg p-8 text-center">
      <Icon icon="mdi:folder-open-outline" style="font-size: 48px;" class="mx-auto mb-4 opacity-60" />
      <p class="text-lg">No projects available for this event yet.</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-6">
      {#each projects as project}
        <div class="card bg-base-200 hover:bg-base-300 transition-colors duration-200 h-full overflow-hidden border {selectedProjects.includes(project.id) ? 'border-accent border-2' : 'border-base-300'}">
          {#if project.image_url}
            <figure class="h-40 overflow-hidden relative">
              <img src={project.image_url} alt={project.name} class="w-full h-full object-cover" />
              {#if selectedProjects.includes(project.id)}
                <div class="absolute top-2 right-2 badge badge-accent">Selected</div>
              {/if}
            </figure>
          {/if}
          <div class="card-body p-5">
            <div class="flex justify-between items-start mb-2">
              <h3 class="card-title text-lg">{project.name}</h3>
              {#if selectedProjects.includes(project.id) && !project.image_url}
                <div class="badge badge-accent">Selected</div>
              {/if}
            </div>
            
            {#if project.description}
              <p class="text-sm opacity-80 mb-4 line-clamp-3">{project.description}</p>
            {:else}
              <p class="text-sm opacity-60 italic mb-4">No description provided</p>
            {/if}
            
            {#if project.collaborators && project.collaborators.length > 0}
              <div class="flex items-center gap-2 mb-3 text-sm">
                <Icon icon="mdi:account-group" style="font-size: 18px;" class="opacity-70" />
                <span>{project.collaborators.length + 1} contributors</span>
              </div>
            {/if}
            
            <div class="flex gap-2 mt-auto">
              {#if project.repo}
                <a href={project.repo} target="_blank" rel="noopener" class="btn btn-sm btn-outline flex-1">
                  <Icon icon="mdi:github" style="font-size: 18px;" />
                  Repo
                </a>
              {/if}
              {#if project.demo}
                <a href={project.demo} target="_blank" rel="noopener" class="btn btn-sm btn-outline flex-1">
                  <Icon icon="mdi:web" style="font-size: 18px;" />
                  Demo
                </a>
              {/if}
              <button 
                class="btn btn-sm {selectedProjects.includes(project.id) ? 'btn-error' : selectedProjects.length >= toSelect ? 'btn-disabled' : 'btn-accent'} flex-1"
                onclick={() => toggleProjectSelection(project.id)}
                disabled={selectedProjects.length >= toSelect && !selectedProjects.includes(project.id)}
              >
                {#if selectedProjects.includes(project.id)}
                  <Icon icon="mdi:close" style="font-size: 18px;" />
                  Remove
                {:else}
                  <Icon icon="mdi:check" style="font-size: 18px;" />
                  Select
                {/if}
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
  
  <div class="mt-8 flex justify-center gap-4">
    <a href={`/events/${event.id}`} class="btn btn-outline">
      <Icon icon="mdi:arrow-left" style="font-size: 20px;" class="mr-2" />
      Back to Event
    </a>
    <button 
      class="btn btn-accent" 
      onclick={submitVote}
      disabled={selectedProjects.length !== toSelect || isSubmitting}
    >
      {#if isSubmitting}
        <span class="loading loading-spinner"></span>
        Submitting...
      {:else}
        <Icon icon="mdi:check-bold" style="font-size: 20px;" class="mr-2" />
        Submit Vote
      {/if}
    </button>
  </div>
</div>
