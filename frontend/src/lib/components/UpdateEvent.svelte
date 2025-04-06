<script lang="ts">
  import { EventsService } from "$lib/client/sdk.gen";
  import type { Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { handleError, invalidateEvents } from "$lib/misc";
  import type { EventUpdate } from "$lib/client/types.gen";
  import { fade } from "svelte/transition";

  let {
    events,
  }: { events: Array<Event> } = $props();

  const emptyEventUpdate: EventUpdate = {
    name: "",
    description: null,
    votable: false
  };
  const emptyEvent: Event = {
    ...emptyEventUpdate,
    owner: [""],
    id: "",
  };
  let event: EventUpdate = $state(emptyEventUpdate);
  let chosenEvent: Event = $state(emptyEvent);
  $inspect(event);

  let showDeleteAlert = $state(false);

  async function deleteEvent() {
    showDeleteAlert = false;
    try {
      await EventsService.deleteEventEventsEventIdDelete({
        path: { event_id: chosenEvent.id },
        throwOnError: true,
      });
      toast("Event deleted successfully");
      // Reset the fields
      event = emptyEventUpdate;
      chosenEvent = emptyEvent;
      // Invalidate events to refresh the list
      invalidateEvents();
    } catch (err) {
      handleError(err);
    }
  }

  async function confirmDeleteEvent() {
    showDeleteAlert = true;
    setTimeout(() => {
      showDeleteAlert = false;
    }, 5000);
  }

  async function updateEvent() {
    try {
      await EventsService.updateEventEventsEventIdPut({
        path: { event_id: chosenEvent.id },
        body: event,
      throwOnError: true,
      });
      toast("Event updated successfully");
      // Reset the fields
      event = emptyEventUpdate;
      chosenEvent = emptyEvent;
      // Invalidate events to refresh the list
      invalidateEvents()
    } catch (err) {
      handleError(err);
    }
  }
</script>

<div class="p-4 max-w-md mx-auto">
  {#if showDeleteAlert}
    <div role="alert" class="alert" in:fade out:fade>
      <span>Are you <strong>sure</strong> you want to delete this event?</span
      >
      <div>
        <button class="btn" onclick={() => (showDeleteAlert = false)}
          >Cancel</button
        >
        <button class="btn btn-error" onclick={() => deleteEvent()}
          >Delete</button
        >
      </div>
    </div>
  {/if}
  <form onsubmit={updateEvent} class="space-y-4">
    <label class="form-control">
      <div class="label">
        <span class="label-text text-primary">Select an event to update</span>
        <span class="label-text-alt">
          This will only show events you own
        </span>
      </div>
      <select
        bind:value={chosenEvent}
        class="select select-bordered"
        onchange={() => {
          event = { ...chosenEvent };
          showDeleteAlert = false;
        }}
      >
        <option value="" disabled selected>Select an event to update</option>
        {#each events as event}
          <option value={event}>{event.name}</option>
        {/each}
      </select>
    </label>
    {#if chosenEvent.id}
    <label class="form-control">
      <div class="label">
        <span class="label-text">Event Name</span>
      </div>
      <input
        type="text"
        bind:value={event.name}
        placeholder="Super cool Hackathon!"
        class="input input-bordered grow"
      />
    </label>

    <!-- Event description field -->
    <label class="form-control">
      <div class="label">
        <span class="label-text">Event Description</span>
      </div>
      <textarea
        bind:value={event.description}
        placeholder="Some cool description"
        class="textarea textarea-bordered grow"
      ></textarea>
    </label>

    <label class="form-control">
      <div class="label">
        <span class="label-text">Votable</span>
      </div>
      <input
        type="checkbox"
        class="checkbox"
        bind:checked={event.votable}
      />
    </label>

      <button type="submit" class="btn btn-block mt-4 btn-primary">
        Update Event
      </button>
      <button
        class="btn btn-block mt-4 btn-warning"
        type="button"
        onclick={() => confirmDeleteEvent()}
      >
        Delete Event
      </button>
    {/if}
  </form>
</div>
