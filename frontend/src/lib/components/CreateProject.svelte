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
  let formErrors = $state({
    name: "",
    description: "",
    image_url: "",
    event: "",
  });
  let submitting = $state(false);

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

  function validate() {
    let isValid = true;

    formErrors = {
      name: "",
      description: "",
      image_url: "",
      event: "",
    };

    if (!project.name.trim()) {
      formErrors.name = "Project name is required";
      isValid = false;
    }

    if (!project.description.trim()) {
      formErrors.description = "Project description is required";
      isValid = false;
    }

    // img url check
    if (project.image_url.trim()) {
      const validExt = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"];
      const isValidExt = validExt.some((ext) =>
        project.image_url.toLowerCase().endsWith(ext),
      );

      if (!isValidExt) {
        formErrors.image_url =
          "Image URL must end with a valid image extension (.jpg, .jpeg, .png, .gif, .webp, .svg)";
        isValid = false;
      }
    }

    if (!project.event[0]) {
      formErrors.event = "Please select an event";
      isValid = false;
    }

    return isValid;
  }

  async function createProject(e: Event) {
    e.preventDefault();

    if (!validate()) {
      toast.error("Please fix the errors in the form");
      return;
    }

    try {
      submitting = true;
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
    } finally {
      submitting = false;
    }
  }
</script>

<div class="p-4 max-w-md mx-auto">
  <form on:submit={createProject} class="space-y-4">
    <label class="form-control">
      <div class="label">
        <span class="label-text">Project Name</span>
      </div>
      <input
        type="text"
        bind:value={project.name}
        placeholder="A really cool project!"
        class="input input-bordered grow"
        class:input-error={formErrors.name}
      />
      {#if formErrors.name}
        <div class="text-error text-sm mt-1">{formErrors.name}</div>
      {/if}
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
        class:textarea-error={formErrors.description}
      ></textarea>
      {#if formErrors.description}
        <div class="text-error text-sm mt-1">{formErrors.description}</div>
      {/if}
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
        class:input-error={formErrors.image_url}
      />
      {#if formErrors.image_url}
        <div class="text-error text-sm mt-1">{formErrors.image_url}</div>
      {/if}
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
        class:select-error={formErrors.event}
        onfocus={() => {
          if (!fetchedEvents) fetchEvents();
        }}
      >
        <option value="" disabled selected>Select an event</option>
        {#each events as event}
          <option value={event.id}>{event.name}</option>
        {/each}
      </select>
      {#if formErrors.event}
        <div class="text-error text-sm mt-1">{formErrors.event}</div>
      {/if}
    </label>
    <button
      type="submit"
      class="btn btn-block btn-primary mt-4"
      disabled={submitting}
    >
      {submitting ? "Creating..." : "Create Project"}
    </button>
  </form>
</div>
