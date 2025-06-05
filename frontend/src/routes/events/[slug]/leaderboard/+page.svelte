<script lang="ts">
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import type { PageData } from "./$types";

  let eventId: string;

  let { data }: { data: PageData } = $props();
  let { projects } = data;
</script>

<div class="container mx-auto p-6">
  <h1 class="text-xl font-semibold mb-4 text-center">Leaderboard</h1>
  <div
    class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mx-auto max-w-4xl"
  >
    {#each projects as project}
      <div class="flex flex-col items-center">
        <ProjectCard
          {project}
          isSelected={false}
          toggle={() => {}}
          selectable={false}
        />
        <div class="badge badge-info badge-lg">Points: {project.points}</div>
      </div>
    {/each}
  </div>
</div>
