<script lang="ts">
  import ProjectCard from "./ProjectCard.svelte";
  import UpdateProjectModal from "./UpdateProjectModal.svelte";
  import Modal from "./Modal.svelte";
  import type { ProjectPrivate, EventPrivate } from "$lib/client/types.gen";
  import type { ValidationResult } from "$lib/validation";

  interface Props {
    project: ProjectPrivate;
    events: EventPrivate[];
    validationResults?: Record<string, ValidationResult>;
  }

  let { project, events, validationResults = {} }: Props = $props();

  let editModal: Modal;
  let validationModal: Modal;
</script>

<div class="m-4">
  <div class="card card-sm bg-base-100 rounded border-1 shadow-sm">
    <!-- Header with metadata -->
    <div class="card-body pb-2">
      <!-- Event name at the top -->
      <div class="text-center mb-3">
        <span class="text-xs text-base-content/70 mb-1 block">Event</span>
        {#each events as event}
          {#if event.id === project.event_id}
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

        <!-- Validation Status -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Status</span>
          <button
            class="badge text-sm px-3 py-1 underline cursor-pointer whitespace-nowrap {validationResults[project.id]?.valid
              ? 'badge-success'
              : 'badge-warning'}"
            onclick={() => validationModal?.openModal()}
            disabled={!validationResults[project.id]}
          >
            {#if !validationResults[project.id]}
              <span class="loading loading-dots loading-xs"></span>
            {:else if validationResults[project.id].valid}
              ✅ Valid
            {:else}
              ❌ Invalid
            {/if}
          </button>

          {#if validationResults[project.id]}
            <Modal title="Validation Details" bind:this={validationModal}>
              <div class="space-y-4">
                <div class="flex items-center gap-2 mb-2">
                  {#if validationResults[project.id].valid}
                    <span class="text-success text-lg">✅ Valid</span>
                  {:else}
                    <span class="text-error text-lg">❌ Invalid</span>
                  {/if}
                </div>
                <p class="text-sm text-base-content/70">{validationResults[project.id].message}</p>
              </div>
            </Modal>
          {/if}
        </div>

        <!-- Actions -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Actions</span>
          <button
            class="badge text-sm px-3 py-1 underline badge-secondary cursor-pointer"
            onclick={() => editModal?.openModal()}
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

<UpdateProjectModal preselectedProject={project} {events} bind:modal={editModal} />
