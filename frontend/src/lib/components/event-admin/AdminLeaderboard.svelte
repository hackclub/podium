<script lang="ts">
  import type { ProjectPublic, EventPrivate } from "$lib/client/types.gen";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { getActiveFeatures } from "$lib/event-features/registry";

  interface Props {
    projects: ProjectPublic[];
    event?: EventPrivate;
  }

  let { projects, event }: Props = $props();

  // Get active event features for this event
  const activeFeatures = $derived(
    event ? getActiveFeatures((event as any).feature_flags_list) : [],
  );
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
            <div class="absolute -top-2 -right-2 z-30">
              <div class="badge badge-primary badge-lg">#{index + 1}</div>
            </div>
            <div class="absolute top-2 left-2 z-10">
              <div
                class="bg-base-100/90 backdrop-blur-sm rounded-lg p-2 text-xs"
              >
                <div class="font-medium">Votes: {project.points || 0}</div>
              </div>
            </div>

            <!-- Event feature validation indicators -->
            {#each activeFeatures as feature}
              {#if feature.validateProject && feature.ValidationComponent}
                {@const validation = feature.validateProject(project)}
                {#await validation then resolved}
                  <feature.ValidationComponent
                    validation={resolved}
                    {project}
                  />
                {/await}
              {/if}
            {/each}

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
