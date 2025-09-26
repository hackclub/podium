<script lang="ts">
  import type { Project } from '$lib/client/types.gen';
  import ProjectCard from '$lib/components/ProjectCard.svelte';

  interface Props {
    projects: Project[];
  }

  let { projects }: Props = $props();
</script>

<div class="card bg-base-200">
  <div class="card-body">
    <h2 class="card-title">Admin Leaderboard ({projects.length})</h2>
    
    {#if projects.length === 0}
      <p class="text-base-content/70">No projects yet.</p>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each projects as project, index}
          <div class="relative">
            <div class="absolute -top-2 -right-2 z-10">
              <div class="badge badge-primary badge-lg">#{index + 1}</div>
            </div>
            <div class="absolute top-2 left-2 z-10">
              <div class="bg-base-100/90 backdrop-blur-sm rounded-lg p-2 text-xs">
                <div class="font-medium">Points: {project.points || 0}</div>
                <div>Votes: {project.votes?.length || 0}</div>
              </div>
            </div>
            <ProjectCard
              {project}
              isSelected={false}
              toggle={() => {}}
              selectable={false}
            />
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>
