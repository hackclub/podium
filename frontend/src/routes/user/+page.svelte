<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
import Collapse from "$lib/components/Collapse.svelte";
    import ProjectCard from "$lib/components/ProjectCard.svelte";
  let { data }: { data: PageData } = $props();

</script>

<div class="text-center p-4">
  <h1 class="text-2xl font-semibold">Hi {data.userData.first_name}!</h1>
  <p class="text-accent">
    {data.userData.email}
  </p>
</div>


  <h1 class="text-xl font-semibold mb-4 text-center">Leaderboard</h1>
  <div
    class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mx-auto max-w-4xl"
  >
    {#each data.projects as project}
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
