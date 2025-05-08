<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { PublicProjectCreationPayload, Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { handleError, invalidateProjects } from "$lib/misc";
  import Modal from "$lib/components/Modal.svelte";

  let project: PublicProjectCreationPayload = $state({
    name: "",
    repo: "",
    demo: "",
    image_url: "",
    description: "",
    event: [""],
    hours_spent: 0,
  });
  let events: Event[] = $state([]);
  let fetchedEvents = false;
  async function fetchEvents() {
    try {
      toast("Fetching events; please wait");
      const { data: userEvents } =
        await EventsService.getAttendingEventsEventsGet({ throwOnError: true });
      events = userEvents.attending_events;
      fetchedEvents = true;
    } catch (err) {
      handleError(err);
    }
  }

  async function createProject() {
    try {
      await ProjectsService.createProjectProjectsPost({
        body: project,
        throwOnError: true,
      });
      toast("Project created successfully");
      project = {
        name: "",
        repo: "",
        demo: "",
        image_url: "",
        description: "",
        event: [""],
        hours_spent: 0,
      };
      invalidateProjects();
    } catch (err) {
      handleError(err);
    }
  }

  let guidelinesModal: Modal = $state() as Modal;
</script>

<div class="p-4 max-w-md mx-auto">
  <!-- <form onsubmit={createProject} class="space-y-4"> -->
  <fieldset class="fieldset">
    <label class="label" for="project_name">Project Name</label>
    <input
      id="project_name"
      type="text"
      bind:value={project.name}
      placeholder="A really cool project!"
      class="input input-bordered grow"
    />

    <label class="label" for="project_description">Project Description</label>
    <textarea
      id="project_description"
      bind:value={project.description}
      placeholder="Some cool description"
      class="textarea textarea-bordered grow"
    ></textarea>

    <label class="label" for="image_url"
      >Image URL for your project's thumbnail</label
    >
    <input
      id="image_url"
      type="text"
      bind:value={project.image_url}
      placeholder="Image URL"
      class="input input-bordered grow"
    />

    <label class="label" for="demo_url"
      >URL to a deployed version of your project</label
    >
    <input
      id="demo_url"
      type="text"
      bind:value={project.demo}
      placeholder="Demo URL"
      class="input input-bordered grow"
    />
    <button
      type="button"
      class="btn-link label"
      onclick={() => {
        guidelinesModal.openModal();
      }}
    >
      What's allowed as a demo?
    </button>

    <label class="label" for="repo_url">Repository URL</label>
    <input
      id="repo_url"
      type="text"
      bind:value={project.repo}
      placeholder="Repository URL"
      class="input input-bordered grow"
    />

    <label class="label" for="hours_spent">Rough estimate of hours spent</label>
    <input
      id="hours_spent"
      type="number"
      bind:value={project.hours_spent}
      placeholder="Hours spent"
      class="input input-bordered grow"
      min="0"
    />

    <label class="label" for="event">Event</label>
    <select
      id="event"
      bind:value={project.event[0]}
      class="select select-bordered"
      onfocus={() => {
        if (!fetchedEvents) fetchEvents();
      }}
    >
      <option value="" disabled selected>Select an event</option>
      {#each events as event}
        <option value={event.id}>{event.name}</option>
      {/each}
    </select>

    <button
      class="btn btn-block btn-primary mt-4"
      onclick={createProject}
    >
      Create Project
    </button>
  </fieldset>
  <!-- </form> -->
</div>

<Modal bind:this={guidelinesModal} title="Demo Guidelines">
  <p class="py-4">
    You should probably check that... Your repo doesn't 404 Your demo link
    doesn't 404 Your demo link isn't a video unless it really really has to be a
    video. Reasons to be a video:
  </p>
  <ul>
    <li>You build a website ❌ nope! you gotta host it</li>
    <li>You built a server and can't host it ❌ nope! you gotta host it</li>
    <li>
      You build something that relies on AI ❌ nope! you still gotta host it
      (see a pattern?)
    </li>
    <li>
      You built a discord bot ⚠️ maybe if it's a really good video, but you
      still have to host it and include a discord bot install link
    </li>
    <li>
      You built a physical robot ✅ this is a good reason for a video, but your
      repo should also include some pics and all the parts & code should be
      open-source
    </li>
  </ul>
</Modal>
