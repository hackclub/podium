<script lang="ts">
  import { EventsService } from "$lib/client/sdk.gen";
  import type { EventPublic } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import type { EventUpdate } from "$lib/client/types.gen";
  import Modal from "$lib/components/Modal.svelte";
  import ConfirmationModal from "$lib/components/ConfirmationModal.svelte";

  let {
    preselectedEvent,
    events,
  }: { preselectedEvent: EventPublic; events: Array<EventPublic> } = $props();

  let updateModal: Modal = $state() as Modal;
  let deleteConfirmation: ConfirmationModal = $state() as ConfirmationModal;

  const emptyEventUpdate: EventUpdate = {
    name: "",
    description: null,
    votable: false,
    leaderboard_enabled: false,
  };

  // Create reactive copy of the event
  let event: EventUpdate = $state({ ...preselectedEvent });

  async function deleteEvent() {
    const { error: err } = await EventsService.deleteEventEventsEventIdDelete({
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

  function confirmDeleteEvent() {
    deleteConfirmation.open();
  }
  async function updateEvent() {
    const { error: err } = await EventsService.updateEventEventsEventIdPut({
      path: { event_id: preselectedEvent.id },
      body: event,
      throwOnError: false,
    });
    if (err) {
      handleError(err);
      return;
    }
    toast.success("Event updated successfully");
    await customInvalidateAll();
    updateModal.closeModal();
  }
</script>

<button
  class="btn btn-sm btn-primary"
  onclick={() => {
    updateModal.openModal();
  }}
>
  Edit Event
</button>
<Modal bind:this={updateModal} title="Update Event">
  <div class="p-4 max-w-md mx-auto">
    <div class="space-y-4">
      <fieldset class="fieldset">
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

        <label class="label" for="demo_links_optional">
          <span>Demo Links Optional</span>
        </label>
        <input
          id="demo_links_optional"
          type="checkbox"
          class="checkbox"
          bind:checked={event.demo_links_optional}
        />

        <button class="btn btn-block mt-4 btn-primary" onclick={updateEvent}>
          Update Event
        </button>
        <button
          class="btn btn-block mt-4 btn-warning"
          type="button"
          onclick={confirmDeleteEvent}
        >
          Delete Event
        </button>
      </fieldset>
    </div>
  </div>
</Modal>

<ConfirmationModal
  bind:this={deleteConfirmation}
  title="Delete Event"
  message="Are you sure you want to delete this event? This action cannot be undone."
  confirmText="Delete"
  cancelText="Cancel"
  confirmClass="btn-error"
  onConfirm={deleteEvent}
  onCancel={() => {}}
/>
