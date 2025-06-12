<svelte:options runes />

<script lang="ts">
  import { toast } from "svelte-sonner";
  import { EventsService } from "$lib/client/sdk.gen";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { handleError, invalidateEvents } from "$lib/misc.js";
  import { getAuthenticatedUser } from "$lib/user.svelte";
    import { invalidateAll } from "$app/navigation";

  let { data } = $props();
  let { event, projects, toSelect, alreadyVoted } = data;
  let selectedProjects: string[] = $state([]);
  let userId = getAuthenticatedUser().user.id;

    

  function toggleProjectSelection(projectId: string) {
    if (selectedProjects.includes(projectId)) {
      // If the project is already selected, remove it from the list
      selectedProjects = selectedProjects.filter((id) => id !== projectId);
    } else {
      if (selectedProjects.length < toSelect) {
        // If the project is not selected and the limit is not reached, add it to the list
        selectedProjects = [...selectedProjects, projectId];
      }
    }
  }

  async function submitVote() {
    try {
      await EventsService.voteEventsVotePost({
        body: {
          event: event.id,
          projects: selectedProjects,
        },
        throwOnError: true,
      });
      toast("Vote submitted successfully");
      invalidateEvents();
      selectedProjects = [];

    } catch (err) {
      handleError(err);
    }
  }
</script>

<!-- Basic information about voting -->
{#if alreadyVoted}
  <div class="p-4 bg-success text-center rounded-xl max-w-2xl mx-auto">
    <p class="text-success-content">
      You have already voted for this event. You can only vote once.
    </p>
  </div>
{:else}
  <div class="p-4 bg-warning text-center rounded-xl max-w-2xl mx-auto">
    <p class="text-warning-content">
      You can vote for {toSelect - selectedProjects.length} more projects in this event.
    </p>
  </div>
  <div class="container mx-auto p-6">
  <div
    class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
  >
    {#each projects as project}
      {#if !(project.owner && project.owner.includes(userId)) && !(project.collaborators && project.collaborators.includes(userId))}
        <ProjectCard
          {project}
          isSelected={selectedProjects.includes(project.id)}
          toggle={() => toggleProjectSelection(project.id)}
          selectable={true}
        />
      {/if}
    {/each}
  </div>
  <!-- Not disabling if user has already voted since this is hidden then anyway -->
  <button class="btn-block btn btn-warning mt-4" onclick={submitVote} disabled={(selectedProjects.length < toSelect)}
    >Submit Vote</button
  >
</div>
{/if}

