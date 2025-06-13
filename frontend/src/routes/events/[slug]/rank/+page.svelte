<svelte:options runes />

<script lang="ts">
  import { toast } from "svelte-sonner";
  import { EventsService } from "$lib/client/sdk.gen";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { handleError, invalidateEvents, invalidateUser } from "$lib/misc.js";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  import { invalidateAll } from "$app/navigation";

  const { data } = $props();
  let selectedProjects: string[] = $state([]);
  let userId = getAuthenticatedUser().user.id;

  function toggleProjectSelection(projectId: string) {
    if (selectedProjects.includes(projectId)) {
      // If the project is already selected, remove it from the list
      selectedProjects = selectedProjects.filter((id) => id !== projectId);
    } else {
      if (selectedProjects.length < data.toSelect) {
        // If the project is not selected and the limit is not reached, add it to the list
        selectedProjects = [...selectedProjects, projectId];
      }
    }
  }

  async function submitVote() {
    try {
      await EventsService.voteEventsVotePost({
        body: {
          event: data.event.id,
          projects: selectedProjects,
        },
        throwOnError: true,
      });
      toast("Vote submitted successfully");
      selectedProjects = [];
      await invalidateUser();
      invalidateEvents();
    } catch (err) {
      handleError(err);
    }
  }
</script>

<!-- Basic information about voting -->
{#if data.alreadyVoted}
  <div class="p-4 bg-success text-center rounded-xl max-w-2xl mx-auto">
    <p class="text-success-content">
      You have already voted for this event. You can only vote once.
    </p>
  </div>
{:else}
  <div class="p-4 bg-warning text-center rounded-xl max-w-2xl mx-auto">
    <p class="text-warning-content text-sm">
      You can vote for {data.toSelect - selectedProjects.length} more projects in
      this event. Projects below don't include projects you have already voted for
      or projects you own or collaborate on. Click on a project to select it for
      voting.
    </p>
  </div>
  <div class="container mx-auto p-6">
    <div
      class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
    >
      {#each data.projects as project}
        <!-- First conditional checks if the user is the owner or a collaborator of the project, in which case they cannot vote for it. Second conditional checks if the user has already voted for this project, in which case they also cannot vote for it. -->
        {#if !(project.owner && project.owner.includes(userId)) && !(project.collaborators && project.collaborators.includes(userId)) && !(project.votes ?? []).some( (vote) => (getAuthenticatedUser().user.votes ?? []).includes(vote), )}
          <ProjectCard
            {project}
            isSelected={selectedProjects.includes(project.id)}
            toggle={() => toggleProjectSelection(project.id)}
            selectable={true}
          />
        {/if}
      {/each}
    </div>
    <!-- Not disabling if user has already voted since this is hidden then anyway. Also not disabling if projects is under toSelect since people can come back. -->
    <button class="btn-block btn btn-warning mt-4" onclick={submitVote}
      >Submit Vote</button
    >
  </div>
{/if}
