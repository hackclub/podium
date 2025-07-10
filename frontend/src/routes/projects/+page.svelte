<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import DOMPurify from "dompurify";
  import type { PageData } from "./$types";
  import ProjectCardWrapper from "$lib/components/ProjectCardWrapper.svelte";
  import { onMount } from "svelte";
  import { ProjectsService, type Results } from "$lib/client";
  import Modal from "$lib/components/Modal.svelte";
  let { data }: { data: PageData } = $props();

  // Stuff for project quality
  const projectModalState = $state({} as Record<string, Modal>);

  // Function to sanitize reasons and replace newlines with <br> tags
  function formatReasons(reasons: string): string {
    return DOMPurify.sanitize(reasons.replace(/\n/g, "<br>"));
  }

  let projectQualityResults: Record<string, Results> = $state({});
  onMount(async () => {
    for (const project of data.projects) {
      const {
        data: qualityData,
        response,
        error: err,
      } = await ProjectsService.checkProjectProjectsCheckPost({
        body: { ...project },
        throwOnError: false,
      });
      if (err || !qualityData) {
        console.error(err, response);
      } else {
        if (qualityData) projectQualityResults[project.id] = qualityData;
      }
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
                events={data.events}
                {projectQualityResults}
                {projectModalState}
                {formatReasons}
              />
            {/key}
          {/each}
        </div>
      {:else}
        <div class="text-center py-8">
          <p class="text-base-content/70 mb-4">You haven't created any projects yet.</p>
          <div class="flex gap-2 justify-center">
            <a href="/projects/create" class="btn btn-primary">Create Project</a>
            <a href="/projects/join" class="btn btn-outline">Join Project</a>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
