<svelte:options runes />

<script lang="ts">
  import { toast } from "svelte-sonner";
  import { EventsService } from "$lib/client/sdk.gen";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { handleError } from "$lib/misc.js";

  let { data } = $props();
  let { event, projects } = data;
  let selectedProjects: string[] = $state([]);
  // let toSelect = $state(projects.length >= 20 ? 3 : 2);
  let toSelect = projects.length >= 20 ? 3 : 2;

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
    // if (
    //   selectedProjects.length < 2 ||
    //   (projects.length >= 20 && selectedProjects.length < 3)
    // ) {
    //   toast("Please select the required number of projects");
    //   return;
    // }
    try {
      await EventsService.voteEventsVotePost({
        body: {
          event: event.id,
          projects: selectedProjects,
        },
        throwOnError: true,
      });
      toast("Vote submitted successfully");
    } catch (err) {
      handleError(err);
    }
  }
</script>

<!-- Basic information about voting -->
<div class="p-4 bg-info text-center rounded-xl max-w-2xl mx-auto">
  <p class="text-info-content">
    Select your top {toSelect} projects in no particular order. If you've voted for less than {toSelect} projects, you can still vote.
  </p>
</div>

<div class="container mx-auto p-6">
  <div
    class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
  >
    {#each projects as project}
      <ProjectCard
        {project}
        isSelected={selectedProjects.includes(project.id)}
        toggle={() => toggleProjectSelection(project.id)}
        selectable={true}
      />
    {/each}
  </div>
  <button class="btn-block btn btn-warning mt-4" onclick={submitVote}
    >Submit Vote</button
  >
</div>
