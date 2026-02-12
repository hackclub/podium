<script lang="ts">
  import type { PageData } from "./$types";
  import ProjectCardWrapper from "$lib/components/ProjectCardWrapper.svelte";
  import { onMount } from "svelte";
  import { validateProject, type ValidationResult } from "$lib/validation";
  let { data }: { data: PageData } = $props();

  let projectQualityResults: Record<string, ValidationResult> = $state({});

  onMount(async () => {
    for (const project of data.projects) {
      const result = await validateProject(project.id);
      projectQualityResults[project.id] = result;
    }
  });
</script>

<div class="max-w-6xl mx-auto space-y-8">
  <!-- Your Projects -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">Your Projects</h2>
      {#if data.projects.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each data.projects as project}
            {#key project.id}
              <ProjectCardWrapper
                {project}
                events={data.events as any}
                validationResults={projectQualityResults}
              />
            {/key}
          {/each}
        </div>
      {:else}
        <div class="text-center py-8">
          <p class="text-base-content/70 mb-4">
            You haven't submitted any projects yet.
          </p>
          <div class="flex gap-2 justify-center">
            <a href="/" class="btn btn-primary">Submit a Project</a>
            <a href="/projects/join" class="btn btn-outline">Join Project</a>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
