<script lang="ts">
  import { handleError, invalidateEvents } from "$lib/misc";
  import { EventsService } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { invalidate } from "$app/navigation";
  // TODO: Use the object instead of individual variables
  let eventName = $state("");
  let eventDescription = $state("");

  // Function to create a new event
  async function createEvent() {
    try {
      const event = { name: eventName, description: eventDescription };
      await EventsService.createEventEventsPost({
        body: event,
        throwOnError: true,
      });
      toast("Event created successfully");
      invalidateEvents();
      // invalidate("events:events")
      // Clear the form
      eventName = "";
      eventDescription = "";
    } catch (err) {
      handleError(err);
    }
  }
</script>

<div class="p-4 max-w-md mx-auto">
  <!-- <form onsubmit={createEvent} class="space-y-2"> -->
  <div class="space-y-2">
    <fieldset class="fieldset">
      <!-- legend removed -->

      <label class="label" for="event_name">Event Name</label>
      <input
        id="event_name"
        type="text"
        bind:value={eventName}
        placeholder="A really cool event"
        class="input input-bordered grow"
      />

      <label class="label" for="event_description">Event Description</label>
      <textarea
        id="event_description"
        bind:value={eventDescription}
        placeholder="Some cool description"
        class="textarea textarea-bordered grow"
      ></textarea>

      <button class="btn btn-block btn-primary mt-4" onclick={createEvent}>
        Create Event
      </button>
    </fieldset>
  </div>
  <!-- </form> -->
</div>
