<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { EventPublic, ProjectPublic } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import type { ProjectPrivate, ProjectUpdate } from "$lib/client/types.gen";
  import { onMount } from "svelte";
  import Modal from "$lib/components/Modal.svelte";
  import ConfirmationModal from "$lib/components/ConfirmationModal.svelte";

  // let events: Event[] = $state([]);
  // let fetchedEvents = false;

  // async function fetchEvents() {
  //   try {
  //     toast("Fetching events; please wait");
  //     const { data: userEvents } =
  //       await EventsService.getAttendingEventsEventsGet({ throwOnError: true });
  //     events = userEvents.attending_events;
  //     fetchedEvents = true;
  //   } catch (err) {
  //     handleError(err);
  //   }
  // }

  let {
    preselectedProject,
    events,
    modal = $bindable(),
  }: { preselectedProject: ProjectPrivate; events: Array<EventPublic>; modal?: Modal } = $props();

  let localModal: Modal = $state() as Modal;
  let deleteConfirmation: ConfirmationModal = $state() as ConfirmationModal;

  // Sync local modal to bindable prop
  $effect(() => {
    if (localModal) {
      modal = localModal;
    }
  });

  // Track the selected event's demo_links_optional setting
  let selectedEvent = $derived(
    events.find((e) => e.id === preselectedProject.event_id),
  );
  let demoLinksOptional = $derived(selectedEvent?.demo_links_optional || false);

  const emptyProjectUpdate: ProjectUpdate = {
    name: "",
    repo: "",
    image_url: "",
    demo: "",
    description: "",
    hours_spent: 0,
  };
  const emptyProject: ProjectPublic = {
    id: "",
    name: "",
    repo: "",
    image_url: "",
    demo: "",
    description: "",
    points: 0,
    owner_id: "",
  };
  // Derive           project = { ...chosenProject };
  let project: ProjectUpdate = $derived({ ...preselectedProject });
  $inspect(project);

  async function deleteProject() {
    const { error: err } =
      await ProjectsService.deleteProjectProjectsProjectIdDelete({
        path: { project_id: preselectedProject.id },
        throwOnError: false,
      });
    if (err) {
      handleError(err);
      return;
    }
    toast.success("Project deleted successfully");
    await customInvalidateAll();
    localModal.closeModal();
  }

  function confirmDeleteProject() {
    deleteConfirmation.open();
  }

  // onMount(() => {
  //   fetchEvents();
  // });

  async function updateProject() {
    const { error: err } =
      await ProjectsService.updateProjectProjectsProjectIdPut({
        path: { project_id: preselectedProject.id },
        body: preselectedProject,
        throwOnError: false,
      });
    if (err) {
      handleError(err);
      return;
    }
    toast.success("Project updated successfully");
    await customInvalidateAll();
    localModal.closeModal();
  }
</script>

<Modal bind:this={localModal} title="Update Project">
  <div class="p-4 max-w-md mx-auto">
    <!-- <form onsubmit={updateProject} class="space-y-4"> -->
    <div class="space-y-4">
      <fieldset class="fieldset">
        <label class="label" for="project_name">Project Name</label>
        <input
          id="project_name"
          type="text"
          bind:value={preselectedProject.name}
          placeholder="A really cool project!"
          class="input input-bordered w-full"
        />

        <label class="label" for="event">Event</label>
        <select
          id="event"
          bind:value={preselectedProject.event_id}
          class="select select-bordered w-full"
        >
          <option value="" disabled selected>Select an event</option>
          {#each events as event}
            <option value={event.id}>{event.name}</option>
          {/each}
        </select>

        <label class="label" for="project_description"
          >Project Description</label
        >
        <textarea
          id="project_description"
          bind:value={preselectedProject.description}
          placeholder="Some cool description"
          class="textarea textarea-bordered w-full"
        ></textarea>

        <label class="label" for="image_url">Image URL</label>
        <input
          id="image_url"
          type="text"
          bind:value={preselectedProject.image_url}
          placeholder="Image URL"
          class="input input-bordered w-full"
        />

        <label class="label" for="demo_url">
          Demo URL
          {#if demoLinksOptional}
            <span class="text-sm text-base-content/70"
              >(Optional for this event)</span
            >
          {/if}
        </label>
        <input
          id="demo_url"
          type="text"
          bind:value={preselectedProject.demo}
          placeholder="Demo URL"
          class="input input-bordered w-full"
        />
        {#if demoLinksOptional}
          <div class="text-sm text-base-content/70 mt-1">
            Demo links are optional for this event. Your project won't be marked
            as invalid if only the demo link fails validation.
          </div>
        {/if}

        <label class="label" for="repo_url">Repository URL</label>
        <input
          id="repo_url"
          type="text"
          bind:value={preselectedProject.repo}
          placeholder="Repository URL"
          class="input input-bordered w-full"
        />

        <label class="label" for="hours_spent">Hours Spent</label>
        <input
          id="hours_spent"
          type="number"
          bind:value={preselectedProject.hours_spent}
          placeholder="Hours spent"
          class="input input-bordered w-full"
          min="0"
        />

        <button class="btn btn-block mt-4 btn-primary" onclick={updateProject}>
          Update Project
        </button>
        <button
          class="btn btn-block mt-4 btn-warning"
          type="button"
          onclick={confirmDeleteProject}
        >
          Delete Project
        </button>
      </fieldset>
    </div>
    <!-- </form> -->
  </div>
</Modal>

<ConfirmationModal
  bind:this={deleteConfirmation}
  title="Delete Project"
  message="Are you sure you want to delete this project? This action cannot be undone."
  confirmText="Delete"
  cancelText="Cancel"
  confirmClass="btn-error"
  onConfirm={deleteProject}
  onCancel={() => {}}
/>
