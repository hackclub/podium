<script lang="ts">
  import ProjectCard from "./ProjectCard.svelte";
  import UpdateProjectModal from "./UpdateProjectModal.svelte";
  import Modal from "./Modal.svelte";
  import type { PrivateProject, Event, Unified } from "$lib/client/types.gen";
  import DOMPurify from "dompurify";

  interface Props {
    project: PrivateProject;
    events: Event[];
    projectQualityResults: Record<string, Unified>;
    projectModalState: Record<string, Modal>;
    formatReasons: (reasons: string) => string;
  }

  let {
    project,
    events,
    projectQualityResults,
    projectModalState,
    formatReasons,
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
          <span class="text-xs text-base-content/70 mb-1">Join Code</span>
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
                {@const result = projectQualityResults[project.id]}
                {@const isReviewFactory = result && 'valid' in result}
                {@const isValid = isReviewFactory ? (result.valid && result.image_valid) : (result as any)?.isValid}
                <button
                  class="badge text-sm px-3 py-1 underline cursor-pointer whitespace-nowrap {isValid
                    ? 'badge-success'
                    : 'badge-warning'}"
                  onclick={() => {
                    projectModalState[project.id].openModal();
                  }}
                  disabled={!result}
                >
                  {#if !result}
                    <span class="loading loading-dots loading-xs"></span>
                  {:else if isValid}
                    ✅ Valid
                  {:else}
                    ❌ Invalid
                  {/if}
                </button>

                {#if result}
                  <!-- Quality Details Modal -->
                  <Modal
                    title="Project Quality"
                    bind:this={projectModalState[project.id]}
                  >
                    {#if isReviewFactory}
                      <div class="space-y-4">
                        <!-- Quality Validation Section -->
                        <div>
                          <h3 class="font-semibold mb-2">Quality Validation</h3>
                          <div class="flex items-center gap-2 mb-2">
                            {#if result.valid}
                              <span class="text-success">✅ Valid</span>
                            {:else}
                              <span class="text-error">❌ Invalid</span>
                            {/if}
                          </div>
                          <p class="text-sm text-base-content/70">
                            {result.reason}
                          </p>
                        </div>

                        <!-- Image Validation Section -->
                        <div>
                          <h3 class="font-semibold mb-2">Image Validation</h3>
                          <div class="flex items-center gap-2 mb-2">
                            {#if result.image_valid}
                              <span class="text-success">✅ Valid</span>
                            {:else}
                              <span class="text-error">❌ Invalid</span>
                            {/if}
                          </div>
                          <p class="text-sm text-base-content/70">
                            {#if result.image_valid}
                              Image URL points to a valid image file
                            {:else}
                              Image URL does not point to a valid image file
                            {/if}
                          </p>
                        </div>
                      </div>
                    {:else}
                      <!-- Event Feature Validation -->
                      <div class="space-y-4">
                        <div class="flex items-center gap-2 mb-2">
                          {#if (result as any).isValid}
                            <span class="text-success text-lg">✅ {(result as any).message}</span>
                          {:else}
                            <span class="text-error text-lg">❌ Validation Failed</span>
                          {/if}
                        </div>
                        <p class="text-sm text-base-content/70">
                          {(result as any).message}
                        </p>
                      </div>
                    {/if}
                  </Modal>
                {/if}
              {/if}
            {/if}
          {/each}
        </div>

        <!-- Actions -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Actions</span>
          <button
            class="badge text-sm px-3 py-1 underline badge-secondary cursor-pointer"
            onclick={() => projectModalState[project.id]?.openModal()}
          >
            Edit
          </button>
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

<UpdateProjectModal preselectedProject={project} {events} modal={projectModalState[project.id]} />
