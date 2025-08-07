<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { ProjectCreationPayload, Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import Modal from "$lib/components/Modal.svelte";

  // Accept callback prop for when project is successfully created
  let { onProjectCreated }: { onProjectCreated?: () => void } = $props();

  let project: ProjectCreationPayload = $state({
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
  
  // Track the selected event's demo_links_optional setting
  let selectedEvent = $derived(events.find(e => e.id === project.event[0]));
  let demoLinksOptional = $derived(selectedEvent?.demo_links_optional || false);
  
  async function fetchEvents() {
    try {
      toast.info("Fetching events; please wait");
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
      toast.success("Project created successfully");
      project = {
        name: "",
        repo: "",
        demo: "",
        image_url: "",
        description: "",
        event: [""],
        hours_spent: 0,
      };
      await customInvalidateAll();
      
      // Call the callback if provided (for auto-progression in SignupWizard)
      if (onProjectCreated) {
        onProjectCreated();
      }
    } catch (err) {
      handleError(err);
    }
  }

  let guidelinesModal: Modal = $state() as Modal;
</script>

<div class="w-full">
  <!-- <form onsubmit={createProject} class="space-y-4"> -->
  <fieldset class="fieldset">
    <div class="flex items-center gap-2 mb-4">
      <div class="tooltip tooltip-right" data-tip="You can always edit this later!">
        <div class="badge badge-info badge-sm">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>
      <span class="text-sm text-base-content/70">You can always edit this later!</span>
    </div>

    <label class="label" for="project_name">Project Name</label>
    <input
      id="project_name"
      type="text"
      bind:value={project.name}
      placeholder="A really cool project!"
      class="input input-bordered w-full"
    />

    <label class="label" for="event">Event</label>
    <select
      id="event"
      bind:value={project.event[0]}
      class="select select-bordered w-full"
      onfocus={() => {
        if (!fetchedEvents) fetchEvents();
      }}
    >
      <option value="" disabled selected>Select an event</option>
      {#each events as event}
        <option value={event.id}>{event.name}</option>
      {/each}
    </select>

    <label class="label" for="project_description">Project Description</label>
    <textarea
      id="project_description"
      bind:value={project.description}
      placeholder="Some cool description"
      class="textarea textarea-bordered w-full"
    ></textarea>

    <label class="label" for="image_url"
      >Image URL for your project's thumbnail</label
    >
    <input
      id="image_url"
      type="text"
      bind:value={project.image_url}
      placeholder="Image URL"
      class="input input-bordered w-full"
    />

    <label class="label" for="demo_url">
      URL to a deployed version of your project
      {#if demoLinksOptional}
        <span class="text-sm text-base-content/70">(Optional for this event)</span>
      {/if}
    </label>
    <input
      id="demo_url"
      type="text"
      bind:value={project.demo}
      placeholder="Demo URL"
      class="input input-bordered w-full"
    />
    {#if demoLinksOptional}
      <div class="text-sm text-base-content/70 mt-1">
        Demo links are optional for this event. Your project won't be marked as invalid if only the demo link fails validation.
      </div>
    {/if}
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
      class="input input-bordered w-full"
    />

    <label class="label" for="hours_spent">Rough estimate of hours spent</label>
    <input
    id="hours_spent"
      type="number"
      bind:value={project.hours_spent}
      placeholder="Hours spent"
      class="input input-bordered w-full"
      min="0"
    />

    <button class="btn btn-accent btn-lg mt-4 btn-block hover:btn-xl transition-all duration-300" onclick={createProject}>
      Ship it!
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
