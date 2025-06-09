<script lang="ts">
  import { EventsService } from "$lib/client/sdk.gen";
  import type { Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { handleError, invalidateEvents } from "$lib/misc";
  import type { EventUpdate } from "$lib/client/types.gen";
  import { fade } from "svelte/transition";

  let { events }: { events: Array<Event> } = $props();

  const emptyEventUpdate: EventUpdate = {
    name: "",
    description: null,
    votable: false,
    leaderboard_enabled: false,
  };
  const emptyEvent: Event = {
    ...emptyEventUpdate,
    owner: [""],
    id: "",
    slug: "",
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
      invalidateEvents();
    } catch (err) {
      handleError(err);
    }
  }
</script>

<div class="p-4 max-w-md mx-auto">
  {#if showDeleteAlert}
    <div role="alert" class="alert" in:fade out:fade>
      <span>Are you <strong>sure</strong> you want to delete this event?</span>
      <div>
        <button class="btn" onclick={() => (showDeleteAlert = false)}>
          Cancel
        </button>
        <button class="btn btn-error" onclick={() => deleteEvent()}>
          Delete
        </button>
      </div>
    </div>
  {/if}
  <!-- <form onsubmit={updateEvent} class="space-y-4"> -->
  <div class="space-y-4">
    <fieldset class="fieldset">
      <!-- legend removed -->

      <label class="label flex justify-between" for="event_select">
        <span class="text-primary">Select an event to update</span>
        <span>This will only show events you own</span>
      </label>
      <select
        id="event_select"
        bind:value={chosenEvent}
        class="select select-bordered w-full"
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

      {#if chosenEvent.id}
        <label class="label" for="event_name">Event Name</label>
        <input
          id="event_name"
          type="text"
          bind:value={event.name}
          placeholder="Super cool Hackathon!"
          class="input input-bordered w-full"
        />

        <label class="label" for="event_description">Event Description</label>
        <textarea
          id="event_description"
          bind:value={event.description}
          placeholder="Some cool description"
          class="textarea textarea-bordered w-full"
        ></textarea>

        <label class="label" for="votable">
          <span>Votable</span>
        </label>
        <input
          id="votable"
          type="checkbox"
          class="checkbox"
          bind:checked={event.votable}
        />

        <label class="label" for="leaderboard_enabled">
          <span>Leaderboard Enabled</span>
        </label>
        <input
          id="leaderboard_enabled"
          type="checkbox"
          class="checkbox"
          bind:checked={event.leaderboard_enabled}
        />

        <button class="btn btn-block mt-4 btn-primary" onclick={updateEvent}>
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
    </fieldset>
  </div>
  <!-- </form> -->
</div>
