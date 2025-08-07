<script lang="ts">
  import { EventsService } from "$lib/client/sdk.gen";
  import type { Event } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import type { EventUpdate } from "$lib/client/types.gen";
  import { fade } from "svelte/transition";
  import Modal from "$lib/components/Modal.svelte";

  let {
    preselectedEvent,
    events,
  }: { preselectedEvent: Event; events: Array<Event> } = $props();

  let updateModal: Modal = $state() as Modal;
  const emptyEventUpdate: EventUpdate = {
    name: "",
    description: null,
    votable: false,
    leaderboard_enabled: false,
  };
  
  // Derive event from preselectedEvent
  let event: EventUpdate = $derived({ ...preselectedEvent });
  $inspect(event);

  let showDeleteAlert = $state(false);
  async function deleteEvent() {
    showDeleteAlert = false;
    const { data, error: err } = await EventsService.deleteEventEventsEventIdDelete({
      path: { event_id: preselectedEvent.id },
      throwOnError: false,
    });
    if (err) {
      handleError(err);
      return;
    }
    toast.success("Event deleted successfully");
    await customInvalidateAll();
    updateModal.closeModal();
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
        path: { event_id: preselectedEvent.id },
        body: preselectedEvent,
        throwOnError: true,
      });
      toast.success("Event updated successfully");
      await customInvalidateAll();
      updateModal.closeModal();
    } catch (err) {
      handleError(err);
    }
  }
</script>

<button class="btn btn-sm btn-primary" onclick={() => {updateModal.openModal()}}>
  Edit Event
</button>
<Modal
  bind:this={updateModal}
  title="Update Event"
>
<div class="p-4 max-w-md mx-auto">
  <div class="space-y-4">
    <fieldset class="fieldset">
      <label class="label" for="event_name">Event Name</label>
      <input
        id="event_name"
        type="text"
        bind:value={preselectedEvent.name}
        placeholder="Super cool Hackathon!"
        class="input input-bordered w-full"
      />

      <label class="label" for="event_description">Event Description</label>
      <textarea
        id="event_description"
        bind:value={preselectedEvent.description}
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
        bind:checked={preselectedEvent.votable}
      />

      <label class="label" for="leaderboard_enabled">
        <span>Leaderboard Enabled</span>
      </label>
      <input
        id="leaderboard_enabled"
        type="checkbox"
        class="checkbox"
        bind:checked={preselectedEvent.leaderboard_enabled}
      />

      <label class="label" for="demo_links_optional">
        <span>Demo Links Optional</span>
      </label>
      <input
        id="demo_links_optional"
        type="checkbox"
        class="checkbox"
        bind:checked={preselectedEvent.demo_links_optional}
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
    </fieldset>
  </div>
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
</div>
</Modal>
