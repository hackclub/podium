<script lang="ts">
  import ProjectCard from "./ProjectCard.svelte";
  import UpdateProjectModal from "./UpdateProjectModal.svelte";
  import Modal from "./Modal.svelte";
  import type { ProjectPrivate, EventPrivate } from "$lib/client/types.gen";
  import { validateProject } from "$lib/validation";
  import { customInvalidateAll } from "$lib/misc";

  interface Props {
    project: ProjectPrivate;
    events: EventPrivate[];
  }

  let { project, events }: Props = $props();

  let editModal = $state<Modal>();
  let validationModal = $state<Modal>();
  let revalidating = $state(false);

  async function triggerRevalidation() {
    revalidating = true;
    try {
      await validateProject(project.id);
      // Give the background task a moment then refresh project data
      await new Promise((r) => setTimeout(r, 1500));
      await customInvalidateAll();
    } finally {
      revalidating = false;
    }
  }

  const statusBadge = $derived(
    project.validation_status === "valid"
      ? { cls: "badge-success", label: "✅ Valid" }
      : project.validation_status === "warning"
        ? { cls: "badge-warning", label: "⚠️ Warning" }
        : { cls: "badge-neutral", label: "Pending" }
  );
</script>

<div class="m-4 min-w-0 @container">
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

      <!-- Narrow: stacked/wrapped.  Wide (@xs+): Status | Join Code (centered) | Edit on one row. -->
      <div class="flex flex-wrap justify-evenly items-start gap-x-3 gap-y-2 text-sm @xs:grid @xs:grid-cols-[auto_minmax(0,1fr)_auto]">
        <!-- Validation Status -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Status</span>
          {#if revalidating}
            <span class="badge badge-sm badge-neutral">
              <span class="loading loading-dots loading-xs"></span>
            </span>
          {:else}
            <button
              class="badge badge-sm underline cursor-pointer whitespace-nowrap {statusBadge.cls}"
              onclick={() => validationModal?.openModal()}
            >
              {statusBadge.label}
            </button>
          {/if}
        </div>

        <!-- Join Code (center) -->
        <div class="flex flex-col items-center justify-self-center">
          <span class="text-xs text-base-content/70 mb-1">Join Code</span>
          <span class="badge badge-accent badge-sm font-mono max-w-full">
            {project.join_code}
          </span>
        </div>

        <!-- Actions -->
        <div class="flex flex-col items-center">
          <span class="text-xs text-base-content/70 mb-1">Actions</span>
          <button
            class="badge badge-sm badge-secondary underline cursor-pointer"
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

<Modal title="Validation Details" bind:this={validationModal}>
  <div class="space-y-4">
    <div class="flex items-center gap-2 mb-2">
      {#if project.validation_status === "valid"}
        <span class="text-success text-lg">✅ Your project looks good!</span>
      {:else if project.validation_status === "warning"}
        <span class="text-warning text-lg">⚠️ Potential issue detected</span>
      {:else}
        <span class="text-base-content/70 text-lg">Validation pending…</span>
      {/if}
    </div>
    {#if project.validation_message}
      <p class="text-sm text-base-content/70">{project.validation_message}</p>
    {/if}
    <p class="text-xs text-base-content/50">
      Validation warnings are informational — your project is never blocked.
    </p>
    <button
      class="btn btn-sm btn-outline"
      onclick={triggerRevalidation}
      disabled={revalidating}
    >
      {revalidating ? "Re-validating…" : "Re-validate"}
    </button>
  </div>
</Modal>

<UpdateProjectModal preselectedProject={project} {events} bind:modal={editModal} />
