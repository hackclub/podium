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
        <span class="text-xs text-base-content/70 mb-1 block">Event</span>
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
          <span class="text-xs text-base-content/70 mb-1">Project Join Code</span>
          <span class="badge badge-accent font-mono text-sm px-3 py-1">
            {project.join_code}
          </span>
        </div>

        <!-- Quality Status -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Status</span>
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
                  class="badge text-sm px-3 py-1 underline cursor-pointer {projectQualityResults[project.id]?.valid
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
                    {#if projectQualityResults[project.id]?.valid}
                      <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                      </svg>
                      Valid
                    {:else}
                      <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                      </svg>
                      Invalid
                    {/if}
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
                          <th>Validity</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>
                            {#if projectQualityResults[project.id]?.valid}
                              <div class="flex items-center">
                                <svg class="w-4 h-4 mr-2 text-success" fill="currentColor" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                                </svg>
                                Valid
                              </div>
                            {:else}
                              <div class="flex items-center">
                                <svg class="w-4 h-4 mr-2 text-error" fill="currentColor" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                                </svg>
                                Invalid
                              </div>
                            {/if}
                          </td>
                          <td>{projectQualityResults[project.id]?.reason}</td>
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
