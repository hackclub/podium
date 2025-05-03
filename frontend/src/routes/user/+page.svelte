<script lang="ts">
  import DOMPurify from "dompurify";
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
  import Collapse from "$lib/components/Collapse.svelte";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { onMount } from 'svelte';
  import { ProjectsService } from '$lib/client/sdk.gen';
  import type { Results } from "$lib/client/types.gen";
  let { data }: { data: PageData } = $props();

  // Create an object with modal element for each project ID
  // acc is accumulated state, project is the current project in the iteration
  const projectModalState = data.projects.reduce((acc, project) => {
    acc[project.id] = null;
    return acc;
  }, {} as Record<string, HTMLDialogElement | null>);

  // Function to toggle the modal state for a specific project ID
  function toggleProjectModal(projectId: string) {
    const modal = projectModalState[projectId];
    if (modal) {
      if (modal.open) {
        modal.close();
      } else {
        modal.showModal();
      }
    }
  }

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

<div class="text-center p-4">
  <h1 class="text-2xl font-semibold">Hi {data.userData.first_name}!</h1>
  <p class="text-accent">{data.userData.email}</p>
</div>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mx-auto max-w-4xl">
  {#each data.projects as project}
    <div class="flex flex-col items-center">
      <ProjectCard
        {project}
        isSelected={false}
        toggle={() => {}}
        selectable={false}
      />
      <button
        class="badge badge-lg underline"
        class:badge-success={projectQualityResults[project.id]?.valid}
        class:badge-warning={!projectQualityResults[project.id]?.valid}
        onclick={() => {
          toggleProjectModal(project.id);
        }}
      >
        {#if !projectQualityResults[project.id]}
          <span class="loading loading-dots loading-xs"></span>
        {:else}
          {projectQualityResults[project.id]?.valid ? "Valid" : "Invalid"}
        {/if}
      </button>
    </div>
    {#if projectQualityResults[project.id]} 
    <!-- This is in a conditional to prevent trying to access null properties -->
    <dialog
      bind:this={projectModalState[project.id]}
      class="modal modal-bottom sm:modal-middle"
    >
      <div class="modal-box">
        <h2 class="font-bold text-lg">Project quality</h2>
        <table class="table w-full table-zebra">
          <thead>
            <tr>
              <th>Check</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Demo</td>
              <td>
                {#if projectQualityResults[project.id]?.demo.valid}
                  ✅
                {:else}
                  ❌ {@html formatReasons(projectQualityResults[project.id]?.demo.reason)}
                {/if}
              </td>
            </tr>
            <tr>
              <td>Source Code</td>
              <td>
                {#if projectQualityResults[project.id]?.source_code.valid}
                  ✅
                {:else}
                  ❌ {@html formatReasons(projectQualityResults[project.id]?.source_code.reason)}
                {/if}
              </td>
            </tr>
            <tr>
              <td>Image URL</td>
              <td>
                {#if projectQualityResults[project.id]?.image_url.valid}
                  ✅
                {:else}
                  ❌ {@html formatReasons(projectQualityResults[project.id]?.image_url.reason)}
                {/if}
              </td>
            </tr>
          </tbody>
        </table>
        <div class="modal-action">
          <button
            class="btn"
            onclick={() => {
              toggleProjectModal(project.id);
            }}>Close</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
    {/if}
  {/each}
</div>
