<script lang="ts">
  import type { Project, PrivateEvent } from "$lib/client/types.gen";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import {
    validateDaydreamURLs,
    isDaydreamEvent,
  } from "$lib/daydreamValidation";

  interface Props {
    projects: Project[];
    event?: PrivateEvent;
  }

  let { projects, event }: Props = $props();

  // Check if this is a daydream event
  const isDaydream = $derived(event ? isDaydreamEvent(event) : false);
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
              <div
                class="bg-base-100/90 backdrop-blur-sm rounded-lg p-2 text-xs"
              >
                <div class="font-medium">Points: {project.points || 0}</div>
                <div>Votes: {project.votes?.length || 0}</div>
              </div>
            </div>

            <!-- Daydream URL validation indicator -->
            {#if isDaydream}
              {@const validation = validateDaydreamURLs(
                project.demo,
                project.repo,
              )}
              <div class="absolute top-2 -right-4 z-20">
                <div
                  class="bg-base-100 shadow-lg border border-base-300 rounded-lg p-3 text-sm max-w-56"
                >
                  <div class="flex items-center gap-2 mb-2">
                    {#if validation.isValid}
                      <div class="badge badge-success badge-sm">✓</div>
                    {:else}
                      <div class="badge badge-error badge-sm">✗</div>
                    {/if}
                    <span class="font-semibold text-sm">URL Check</span>
                  </div>
                  <div
                    class="text-sm font-medium {validation.isValid
                      ? 'text-success'
                      : 'text-red-600'} break-words"
                  >
                    {validation.message}
                  </div>
                  {#if validation.swagEligible}
                    <div class="text-sm text-success font-semibold mt-2">
                      🎁 Eligible for swag!
                    </div>
                  {/if}
                </div>
              </div>
            {/if}

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
