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
      const event = { name: eventName, description: eventDescription };
      const {error: err} = await EventsService.createEventEventsPost({
        body: event,
        throwOnError: false,
      });
      if  (err) {
          handleError(err);
          return;
      }
      toast("Event created successfully");
      await invalidateEvents();
      // Clear the form
      eventName = "";
      eventDescription = "";
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
        class="input input-bordered w-full"
      />

      <label class="label" for="event_description">Event Description</label>
      <textarea
        id="event_description"
        bind:value={eventDescription}
        placeholder="Some cool description"
        class="textarea textarea-bordered w-full"
      ></textarea>

      <button class="btn btn-block btn-primary mt-4" onclick={createEvent}>
        Create Event
      </button>
    </fieldset>
  </div>
  <!-- </form> -->
</div>
