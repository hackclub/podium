<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { Event, Project } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError, invalidateProjects } from "$lib/misc";
  import type { PrivateProject, ProjectUpdate } from "$lib/client/types.gen";
  import { fade } from "svelte/transition";
  import { onMount } from "svelte";
  import Modal from "$lib/components/Modal.svelte";


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
    }: { preselectedProject: PrivateProject; events: Array<Event>} = $props();
  
  let updateModal: Modal = $state() as Modal;

  const emptyProjectUpdate: ProjectUpdate = {
    name: "",
    repo: "",
    image_url: "",
    demo: "",
    description: "",
    event: [""],
    hours_spent: 0,
  };
  const emptyProject: Project = {
    ...emptyProjectUpdate,
    owner: [""],
    event: [""],
    id: "",
  };
  // Derive           project = { ...chosenProject };
  let project: ProjectUpdate  = $derived({ ...preselectedProject })
  $inspect(project);

  let showDeleteAlert = $state(false);

  async function deleteProject() {
    showDeleteAlert = false;
      const {data, error: err} = await ProjectsService.deleteProjectProjectsProjectIdDelete({
        path: { project_id: preselectedProject.id },
        throwOnError: false,
      });
      if (err) {
        handleError(err);
        return;
      }
      toast.success("Project deleted successfully");
      await customInvalidateAll();
      updateModal.closeModal();
  }

  async function confirmDeleteProject() {
    showDeleteAlert = true;
    setTimeout(() => {
      showDeleteAlert = false;
    }, 5000);
  }

  // onMount(() => {
  //   fetchEvents();
  // });

  async function updateProject() {
    try {
      await ProjectsService.updateProjectProjectsProjectIdPut({
        path: { project_id: preselectedProject.id },
        body: preselectedProject,
        throwOnError: true,
      });
      toast.success("Project updated successfully");
      await invalidateProjects();
      updateModal.closeModal();
    } catch (err) {
      handleError(err);
    }
  }
</script>

  <button class="badge badge-lg underline badge-secondary" onclick={() => {updateModal.openModal()}}>
    Update
  </button>
  <Modal
    bind:this={updateModal}
    title="Update Project"
  >
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

        <label class="label" for="demo_url">Demo URL</label>
        <input
          id="demo_url"
          type="text"
          bind:value={preselectedProject.demo}
          placeholder="Demo URL"
          class="input input-bordered w-full"
        />

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

        <label class="label" for="event">Event</label>
        <select
          id="event"
          bind:value={preselectedProject.event[0]}
          class="select select-bordered w-full"
        >
          <option value="" disabled selected>Select an event</option>
          {#each events as event}
            <option value={event.id}>{event.name}</option>
          {/each}
        </select>

        <button class="btn btn-block mt-4 btn-primary" onclick={updateProject}>
          Update Project
        </button>
        <button
          class="btn btn-block mt-4 btn-warning"
          type="button"
          onclick={() => confirmDeleteProject()}
        >
          Delete Project
        </button>
    </fieldset>
  </div>
  <!-- </form> -->
    {#if showDeleteAlert}
    <div role="alert" class="alert" in:fade out:fade>
      <span>Are you <strong>sure</strong> you want to delete this project?</span
      >
      <div>
        <button class="btn" onclick={() => (showDeleteAlert = false)}>
          Cancel
        </button>
        <button class="btn btn-error" onclick={() => deleteProject()}>
          Delete
        </button>
      </div>
    </div>
  {/if}
</div>
</Modal>