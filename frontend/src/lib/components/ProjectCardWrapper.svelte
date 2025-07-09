<script lang="ts">
  import ProjectCard from "./ProjectCard.svelte";
  import UpdateProject from "./UpdateProject.svelte";
  import Modal from "./Modal.svelte";
  import type { PrivateProject, Event, Results } from "$lib/client/types.gen";
  import DOMPurify from "dompurify";

  interface Props {
    project: PrivateProject;
    events: Event[];
    projectQualityResults: Record<string, Results>;
    projectModalState: Record<string, Modal>;
    formatReasons: (reasons: string) => string;
  }

  let { 
    project, 
    events, 
    projectQualityResults, 
    projectModalState, 
    formatReasons 
  }: Props = $props();
</script>

<div class="m-4">
  <div class="card card-sm bg-base-100 rounded border-1 shadow-sm">
    <!-- Header with metadata -->
    <div class="card-body pb-2">
      <!-- Event name at the top -->
      <div class="text-center mb-3">
        {#each events as event}
          {#if event.id === project.event[0]}
            <a
              href={`/events/${event.slug}`}
              class="link link-primary text-sm font-medium"
              data-sveltekit-noscroll
            >
              {event.name}
            </a>
          {/if}
        {/each}
      </div>
      
      <div class="grid grid-cols-3 gap-3 text-sm">
        <!-- Join Code -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Join Code</span>
          <div class="tooltip" data-tip="Click to copy join link">
            <a
              href={`/projects/?join_code=${project.join_code}`}
              data-sveltekit-noscroll
              class="badge badge-accent font-mono text-sm px-3 py-1 underline"
            >
              {project.join_code}
            </a>
          </div>
        </div>

        <!-- Quality Status -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Quality</span>
          {#each events as event}
            {#if event.id === project.event[0]}
              {#if event.ysws_checks_enabled === false}
                <span
                  class="tooltip tooltip-bottom underline cursor-help badge badge-neutral text-sm px-3 py-1"
                  data-tip="The event owner disabled automatic quality checks"
                >
                  N/A
                </span>
              {:else}
                <button
                  class="badge text-sm px-3 py-1 underline {projectQualityResults[project.id]?.valid
                    ? 'badge-success'
                    : 'badge-warning'}"
                  onclick={() => {
                    projectModalState[project.id].openModal();
                  }}
                  disabled={!projectQualityResults[project.id]}
                >
                  {#if !projectQualityResults[project.id]}
                    <span class="loading loading-dots loading-xs"></span>
                  {:else}
                    {projectQualityResults[project.id]?.valid ? "Valid" : "Invalid"}
                  {/if}
                </button>
                {#if projectQualityResults[project.id]}
                  <!-- Quality Details Modal -->
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
                                projectQualityResults[project.id]?.demo.reason,
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
                                projectQualityResults[project.id]?.source_code.reason,
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
                                projectQualityResults[project.id]?.image_url.reason,
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
        </div>

        <!-- Actions -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Actions</span>
          <UpdateProject preselectedProject={project} {events} />
        </div>
      </div>
      
      <div class="divider my-1"></div>
    </div>

    <!-- Remove the outer margin from ProjectCard since we're handling it here -->
    <div class="card-body pt-0 pb-4">
      <div class="-m-4 -mt-2">
        <ProjectCard
          {project}
          isSelected={false}
          toggle={() => {}}
          selectable={false}
        />
      </div>
    </div>
  </div>
</div>
