<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import DOMPurify from "dompurify";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
  import Collapse from "$lib/components/Collapse.svelte";
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

<div class="p-4 mx-auto space-y-4">
  <section>
    <Collapse title="Your projects">
      <div class="overflow-x-auto">
        <table class="table w-full table-zebra">
          <thead>
            <tr>
              <th>Project</th>
              <th>Join Code</th>
              <th>Quality</th>
              <th>Event</th>
              <th>Update</th>
            </tr>
          </thead>
          <tbody>
            {#each data.projects as project}
              {#key project.id}
                <tr>
                  <td class="w-1/2">
                    <!-- container to make the card smaller -->
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
                    <a
                      href={`/projects/?join_code=${project.join_code}`}
                      data-sveltekit-noscroll
                      class="hover-link"
                    >
                      {project.join_code}
                    </a>
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
                          class="hover-link"
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
    </Collapse>
  </section>
  <section>
    <Collapse title="Create a project">
      <CreateProject />
    </Collapse>
  </section>
  <section>
    <Collapse title="Join a project">
      <JoinProject />
    </Collapse>
  </section>
</div>

<style>
  /* section {
    @apply p-6 rounded-lg shadow-xs border-accent/50 border-2 border-dotted;
  } */
</style>
