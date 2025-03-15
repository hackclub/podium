<script lang="ts">
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { PublicProjectCreationPayload, Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { handleError } from "$lib/misc";

  let project: PublicProjectCreationPayload = $state({
    name: "",
    readme: "https://example.com",
    repo: "",
    demo: "",
    image_url: "",
    description: "",
    event: [""],
    hours_spent: 0,
  });
  let events: Event[] = $state([]);
  let fetchedEvents = false;
  let showGuidelines = $state(false);
  let guidelinesModal: HTMLDialogElement | null = $state(null);
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
        readme: "https://example.com",
        repo: "",
        demo: "",
        image_url: "",
        description: "",
        event: [""],
        hours_spent: 0,
      };
    } catch (err) {
      handleError(err);
    }
  }

  function toggleGuidelines() {
    showGuidelines = !showGuidelines;
    if (guidelinesModal) {
    if (showGuidelines) {
      guidelinesModal.showModal();
    } else {
      guidelinesModal.close();
    }
  }
  }
</script>

<div class="p-4 max-w-md mx-auto">
  <form onsubmit={createProject} class="space-y-4">
    <label class="form-control">
      <div class="label">
        <span class="label-text">Project Name</span>
      </div>
      <input
        type="text"
        bind:value={project.name}
        placeholder="A really cool project!"
        class="input input-bordered grow"
      />
    </label>
    <!-- Project description field -->
    <label class="form-control">
      <div class="label">
        <span class="label-text">Project Description</span>
      </div>
      <textarea
        bind:value={project.description}
        placeholder="Some cool description"
        class="textarea textarea-bordered grow"
      ></textarea>
    </label>
    <label class="form-control">
      <div class="label">
        <span class="label-text">Image URL for your project's thumbnail</span>
        <span class="label-text-alt">
          (such as a raw GitHub link or a #cdn link)</span
        >
      </div>
      <input
        type="text"
        bind:value={project.image_url}
        placeholder="Image URL"
        class="input input-bordered grow"
      />
    </label>
    <label class="form-control">
      <div class="label">
        <span class="label-text">URL to a deployed version of your project</span>
        <span class="label-text-alt"> (a link to an interactive demo)</span>
      </div>
      <input
        type="text"
        bind:value={project.demo}
        placeholder="Demo URL"
        class="input input-bordered grow"
      />
      <div class="label">
        <span class="label-text">
        <button type="button" class="btn-link" onclick={toggleGuidelines}>What's allowed as a demo?</button>
        </span>
      </div>
    </label>
    <label class="form-control">
      <div class="label">
        <span class="label-text">Repository URL</span>
        <span class="label-text-alt"> (such as a GitHub link)</span>
      </div>
      <input
        type="text"
        bind:value={project.repo}
        placeholder="Repository URL"
        class="input input-bordered grow"
      />
    </label>
    <label class="form-control">
      <div class="label">
        <span class="label-text"
          >Rough estimate of how many hours you (individually) spent on this project</span
        >
      </div>
      <input
        type="number"
        bind:value={project.hours_spent}
        placeholder="Hours spent"
        class="input input-bordered grow"
        min="0"
      />
      <div class="label">
        <span class="label-text-alt">
          This is only used for statistics, so please be honest!</span
        >
      </div>
    </label>
    <label class="form-control">
      <div class="label">
        <span class="label-text">Event</span>
      </div>
      <select
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
    </label>
    <button type="submit" class="btn btn-block btn-primary mt-4">
      Create Project
    </button>
  </form>
</div>



<dialog bind:this={guidelinesModal} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box">
      <h2 class="font-bold text-lg">Demo guidelines</h2>
      <p class="py-4">
        You should probably check that...
        Your repo doesn't 404
        Your demo link doesn't 404
        Your demo link isn't a video unless it really really has to be a video. Reasons to be a video:
      </p>
      <ul>
        <li>You build a website ❌ nope! you gotta host it</li>
        <li>You built a server and can't host it ❌ nope! you gotta host it</li>
        <li>You build something that relies on AI ❌ nope! you still gotta host it (see a pattern?)</li>
        <li>You built a discord bot ⚠️ maybe if it's a really good video, but you still have to host it and include a discord bot install link</li>
        <li>You built a physical robot ✅ this is a good reason for a video, but your repo should also include some pics and all the parts & code should be open-source</li>
      </ul>
        <div class="modal-action">
        <button
          class="btn"
          onclick={() => {
            toggleGuidelines();
          }}>Close</button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>   
  </dialog>