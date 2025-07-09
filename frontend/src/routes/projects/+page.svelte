<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import DOMPurify from "dompurify";
  import type { PageData } from "./$types";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
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
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">My Projects</h1>
    <p class="text-base-content/70">Manage your hackathon projects and track their quality.</p>
  </div>

  <!-- Your Projects -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">Your Projects</h2>
      {#if data.projects.length > 0}
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>Project</th>
                <th>Join Code</th>
                <th>Quality</th>
                <th>Event</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each data.projects as project}
                {#key project.id}
                  <tr>
                    <td class="w-1/2">
                      <div>
                        <ProjectCard
                          {project}
                          isSelected={false}
                          toggle={() => {}}
                          selectable={false}
                        />
                      </div>
                    </td>
                    <td>
                      <div class="tooltip" data-tip="Click to copy join link">
                        <a
                          href={`/projects/?join_code=${project.join_code}`}
                          data-sveltekit-noscroll
                          class="badge badge-accent font-mono"
                        >
                          {project.join_code}
                        </a>
                      </div>
                    </td>
                    <td>
                      {#each data.events as event}
                        {#if event.id === project.event[0]}
                          {#if event.ysws_checks_enabled === false}
                            <span
                              class="tooltip tooltip-left underline cursor-help"
                              data-tip="The event owner disabled automatic quality checks"
                              >N/A</span
                            >
                          {:else}
                            <button
                              class="badge badge-lg underline {projectQualityResults[
                                project.id
                              ]?.valid
                                ? 'badge-success'
                                : 'badge-warning'}"
                              onclick={() => {
                                projectModalState[project.id].openModal();
                              }}
                              disabled={!projectQualityResults[project.id]}
                            >
                              {#if !projectQualityResults[project.id]}
                                <span class="loading loading-dots loading-xs"
                                ></span>
                              {:else}
                                {projectQualityResults[project.id]?.valid
                                  ? "Valid"
                                  : "Invalid"}
                              {/if}
                            </button>
                            {#if projectQualityResults[project.id]}
                              <!-- This is in a conditional to prevent trying to access null properties -->
                              <Modal
                                title="Project Quality"
                                bind:this={projectModalState[project.id]}
                              >
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
                                          ❌ {@html formatReasons(
                                            projectQualityResults[project.id]
                                              ?.demo.reason,
                                          )}
                                        {/if}
                                      </td>
                                    </tr>
                                    <tr>
                                      <td>Source Code</td>
                                      <td>
                                        {#if projectQualityResults[project.id]?.source_code.valid}
                                          ✅
                                        {:else}
                                          ❌ {@html formatReasons(
                                            projectQualityResults[project.id]
                                              ?.source_code.reason,
                                          )}
                                        {/if}
                                      </td>
                                    </tr>
                                    <tr>
                                      <td>Image URL</td>
                                      <td>
                                        {#if projectQualityResults[project.id]?.image_url.valid}
                                          ✅
                                        {:else}
                                          ❌ {@html formatReasons(
                                            projectQualityResults[project.id]
                                              ?.image_url.reason,
                                          )}
                                        {/if}
                                      </td>
                                    </tr>
                                  </tbody>
                                </table>
                              </Modal>
                            {/if}
                          {/if}
                        {/if}
                      {/each}
                    </td>
                    <td>
                      {#each data.events as event}
                        {#if event.id === project.event[0]}
                          <a
                            href={`/events/${event.slug}`}
                            class="link link-primary"
                            data-sveltekit-noscroll>{event.name}</a
                          >
                        {/if}
                      {/each}
                    </td>
                    <td>
                      <UpdateProject
                        preselectedProject={project}
                        events={data.events}
                      />
                    </td>
                  </tr>
                {/key}
              {/each}
            </tbody>
          </table>
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
