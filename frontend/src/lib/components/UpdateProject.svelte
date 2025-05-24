<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { Event, Project } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { handleError, invalidateProjects } from "$lib/misc";
  import type { PrivateProject, ProjectUpdate } from "$lib/client/types.gen";
  import { fade } from "svelte/transition";
  import { onMount } from "svelte";

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
    projects,
    events,
  }: { projects: Array<PrivateProject>; events: Array<Event> } = $props();

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
  let project: ProjectUpdate = $state(emptyProjectUpdate);
  let chosenProject: Project = $state(emptyProject);
  $inspect(project);
  let fetchedProjects = false;

  let showDeleteAlert = $state(false);

  // async function fetchProjects() {
  //   try {
  //     toast("Fetching projects...");
  //     const { data } = await ProjectsService.getProjectsProjectsMineGet({
  //       throwOnError: true,
  //     });
  //     projects = data;
  //     fetchedProjects = true;
  //   } catch (err) {
  //     handleError(err);
  //   }
  // }

  async function deleteProject() {
    showDeleteAlert = false;
    try {
      await ProjectsService.deleteProjectProjectsProjectIdDelete({
        path: { project_id: chosenProject.id },
        throwOnError: true,
      });
      toast("Project deleted successfully");
      // Reset the fields
      project = emptyProjectUpdate;
      chosenProject = emptyProject;
      // Fetch the projects again if the user wants to perform another update to reflect the deletion
      fetchedProjects = false;
      invalidateProjects(); 
    } catch (err) {
      handleError(err);
    }
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
        path: { project_id: chosenProject.id },
        body: project,
      throwOnError: true,
      });
      toast("Project updated successfully");
      // Reset the fields
      project = emptyProjectUpdate;
      chosenProject = emptyProject;
      // fetch the projects again if the user wants to perform another update
      fetchedProjects = false;
      invalidateProjects();  
    } catch (err) {
      handleError(err);
    }
  }
</script>

<div class="p-4 max-w-md mx-auto">
  {#if showDeleteAlert}
    <div role="alert" class="alert" in:fade out:fade>
      <span>Are you <strong>sure</strong> you want to delete this project?</span>
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
  <!-- <form onsubmit={updateProject} class="space-y-4"> -->
  <div class="space-y-4">
    <fieldset class="fieldset">
      <label class="label" for="project_select">
        <span class="text-primary">Choose a project to update</span>
        <span class="text-sm">This will only show projects you own</span>
      </label>
      <select
        id="project_select"
        bind:value={chosenProject}
        class="select select-bordered w-full"
        onchange={() => {
          project = { ...chosenProject };
          showDeleteAlert = false;
        }}
      >
        <option value="" disabled selected>Select a project to update</option>
        {#each projects as project}
          <option value={project}>{project.name}</option>
        {/each}
      </select>

      {#if chosenProject.id}
        <label class="label" for="project_name">Project Name</label>
        <input
          id="project_name"
          type="text"
          bind:value={project.name}
          placeholder="A really cool project!"
          class="input input-bordered w-full"
        />

        <label class="label" for="project_description">Project Description</label>
        <textarea
          id="project_description"
          bind:value={project.description}
          placeholder="Some cool description"
          class="textarea textarea-bordered w-full"
        ></textarea>

        <label class="label" for="image_url">Image URL</label>
        <input
          id="image_url"
          type="text"
          bind:value={project.image_url}
          placeholder="Image URL"
          class="input input-bordered w-full"
        />

        <label class="label" for="demo_url">Demo URL</label>
        <input
          id="demo_url"
          type="text"
          bind:value={project.demo}
          placeholder="Demo URL"
          class="input input-bordered w-full"
        />

        <label class="label" for="repo_url">Repository URL</label>
        <input
          id="repo_url"
          type="text"
          bind:value={project.repo}
          placeholder="Repository URL"
          class="input input-bordered w-full"
        />

        <label class="label" for="hours_spent">Hours Spent</label>
        <input
          id="hours_spent"
          type="number"
          bind:value={project.hours_spent}
          placeholder="Hours spent"
          class="input input-bordered w-full"
          min="0"
        />

        <label class="label" for="event">Event</label>
        <select
          id="event"
          bind:value={project.event[0]}
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
      {/if}
    </fieldset>
  </div>
  <!-- </form> -->
</div>
