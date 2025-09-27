<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { ProjectCreationPayload, Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import Modal from "$lib/components/Modal.svelte";

  // Accept callback prop for when project is successfully created
  // Accept optional event to pre-fill and hide the event selector
  let { onProjectCreated, preselectedEvent }: { 
    onProjectCreated?: () => void;
    preselectedEvent?: Event;
  } = $props();

  let project: ProjectCreationPayload = $state({
    name: "",
    repo: "",
    demo: "",
    image_url: "",
    description: "",
    event: [preselectedEvent?.id || ""],
    hours_spent: 0,
  });
  let events: Event[] = $state([]);
  let fetchedEvents = false;
  
  // Track the selected event's demo_links_optional setting
  let selectedEvent = $derived(
    preselectedEvent || events.find(e => e.id === project.event[0])
  );
  let demoLinksOptional = $derived(selectedEvent?.demo_links_optional || false);
  
  async function fetchEvents() {
    toast.info("Fetching events; please wait");
    const { data: userEvents, error: err } =
      await EventsService.getAttendingEventsEventsGet({ throwOnError: false });
    if (err || !userEvents) {
      handleError(err);
      return;
    }
    events = userEvents.attending_events;
    fetchedEvents = true;
  }

  async function createProject() {
    const { data, error: err } = await ProjectsService.createProjectProjectsPost({
      body: project,
      throwOnError: false,
    });
    if (err) {
      handleError(err);
      return;
    }
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
  }

  let guidelinesModal: Modal = $state() as Modal;

  // URL validation regexes
  const itchioRegex = /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/;
  const githubRegex = /^(https?:\/\/)?(github\.com|gitee\.com)\/[a-zA-Z0-9\-_]+\/[a-zA-Z0-9\-_.]+/;

  // Validation state
  let demoUrlValid = $derived(!project.demo || itchioRegex.test(project.demo));
  let repoUrlValid = $derived(!project.repo || githubRegex.test(project.repo));
</script>

<div class="w-full">
  <!-- <form onsubmit={createProject} class="space-y-4"> -->
  <fieldset class="fieldset">
    <div class="flex items-center gap-2 mb-4">
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

    {#if !preselectedEvent}
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
    {/if}

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
      Playable Itch.io URL for your game
      {#if demoLinksOptional}
        <span class="text-sm text-base-content/70">(Optional for this event)</span>
      {/if}
    </label>
    <input
      id="demo_url"
      type="text"
      bind:value={project.demo}
      placeholder="https://yourname.itch.io/gamename"
      class="input input-bordered w-full {project.demo && !demoUrlValid ? 'input-error' : ''}"
    />
    {#if project.demo && !demoUrlValid}
      <div class="text-[#cf4960] text-sm mt-1">
        Please enter a valid itch.io URL (format: https://username.itch.io/gamename)
      </div>
    {/if}
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

    <label class="label" for="repo_url">GitHub URL</label>
    <input
      id="repo_url"
      type="text"
      bind:value={project.repo}
      placeholder="https://github.com/yourname/gamename"
      class="input input-bordered w-full {project.repo && !repoUrlValid ? 'input-error' : ''}"
    />
    {#if project.repo && !repoUrlValid}
      <div class="text-[#cf4960] text-sm mt-1">
        Please enter a valid GitHub URL (format: https://github.com/username/repository)
      </div>
    {/if}

    <label class="label" for="hours_spent">Rough estimate of hours spent</label>
    <input
    id="hours_spent"
      type="number"
      bind:value={project.hours_spent}
      placeholder="Hours spent"
      class="input input-bordered w-full"
      min="0"
    />

    <button 
      class="btn btn-accent btn-lg mt-4 btn-block hover:btn-xl transition-all duration-300" 
      onclick={createProject}
      disabled={!demoUrlValid || !repoUrlValid}
    >
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
