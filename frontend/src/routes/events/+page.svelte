<svelte:options runes />

<script lang="ts">
  import AttendEvent from "$lib/components/AttendEvent.svelte";
  import CreateEvent from "$lib/components/CreateEvent.svelte";
  import { EventsService } from "$lib/client";
  import type { PageData } from "./$types";
  import { handleError } from "$lib/misc";
  import Icon from "@iconify/svelte";
  import Collapse from "$lib/components/Collapse.svelte";

  let { data }: { data: PageData } = $props();

  let showAttendModal = $state(false);
  let showCreateModal = $state(false);
  let attendingEventsExpanded = $state(true);
  let ownedEventsExpanded = $state(true);

  async function onVotableCheck(value: boolean, eventId: string) {
    try {
      console.log(value, eventId);
      await EventsService.makeVotableEventsMakeVotablePost({
        query: { votable: value, event_id: eventId },
        throwOnError: true,
      });
    } catch (err) {
      handleError(err);
    }
  }

  function toggleAttendingEvents() {
    const element = document.getElementById('attending-events');
    if (element) {
      element.classList.toggle('hidden');
      attendingEventsExpanded = !attendingEventsExpanded;
    }
  }

  function toggleOwnedEvents() {
    const element = document.getElementById('owned-events');
    if (element) {
      element.classList.toggle('hidden');
      ownedEventsExpanded = !ownedEventsExpanded;
    }
  }

  function openAttendModal() {
    showAttendModal = true;
  }

  function closeAttendModal() {
    showAttendModal = false;
  }

  function openCreateModal() {
    showCreateModal = true;
  }

  function closeCreateModal() {
    showCreateModal = false;
  }
</script>

<div class="max-w-6xl mx-auto py-8 px-6">
  <section class="mb-8 text-center">
    <h1 class="text-3xl font-medium mb-3">Events Dashboard</h1>
    <p class="text-lg opacity-80 max-w-2xl mx-auto">
      Manage your hackathon events, join new ones, and track your participation.
    </p>
  </section>
  
  <div class="grid gap-8">
    <!-- Attending Events Section -->
    <div class="collapsible-container p-6 rounded-lg">
      <div class="collapse-header" onclick={toggleAttendingEvents}>
        <h2 class="text-xl font-medium">Events you're attending</h2>
        <Icon icon={attendingEventsExpanded ? "mdi:chevron-up" : "mdi:chevron-down"} style="font-size: 24px;" />
      </div>
      <div id="attending-events" class="mt-4">
        <div class="overflow-x-auto">
          <table class="table table-lg w-full table-zebra">
            <thead>
              <tr>
                <th class="text-base">Event Name</th>
                <th class="text-base">Description</th>
              </tr>
            </thead>
            <tbody>
              {#each data.events.attending_events as event}
                <tr>
                  <td class="font-medium">
                    <a href={`/events/${event.id}`} class="hover:underline text-accent hover:text-accent/80 transition-colors">{event.name}</a>
                  </td>
                  <td>{event.description}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- Owned Events Section -->
    <div class="collapsible-container p-6 rounded-lg">
      <div class="collapse-header" onclick={toggleOwnedEvents}>
        <h2 class="text-xl font-medium">Owned Events</h2>
        <Icon icon={ownedEventsExpanded ? "mdi:chevron-up" : "mdi:chevron-down"} style="font-size: 24px;" />
      </div>
      <div id="owned-events" class="mt-4">
        <div class="overflow-x-auto">
          <table class="table table-lg w-full table-zebra">
            <thead>
              <tr>
                <th class="text-base">Event Name</th>
                <th class="text-base">Description</th>
                <th class="text-base">Join Code</th>
                <th class="text-base">Votable</th>
              </tr>
            </thead>
            <tbody>
              {#each data.events.owned_events as event}
                <tr>
                  <td class="font-medium">
                    <a href={`/events/${event.id}`} class="hover:underline text-accent hover:text-accent/80 transition-colors">{event.name}</a>
                  </td>
                  <td>{event.description}</td>
                  <td>
                    <a
                      href={`/events/?join_code=${event.join_code}`}
                      data-sveltekit-noscroll class="hover:underline font-mono text-accent/90 hover:text-accent transition-colors">{event.join_code}</a>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      class="checkbox checkbox-accent"
                      checked={event.votable}
                      onchange={(e) =>
                        onVotableCheck(
                          (e.target as HTMLInputElement).checked,
                          event.id,
                        )}
                    />
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex justify-center gap-6 mt-4">
      <button class="btn btn-info" onclick={openAttendModal}>
        <Icon icon="mdi:heart" style="font-size: 24px;"/>
        Attend Event
      </button>
      <button class="btn btn-info" onclick={openCreateModal}>
        <Icon icon="icons8:plus" style="font-size: 24px;" />
        Create Event
      </button>
    </div>
  </div>
</div>

<!-- Attend Event Modal -->
{#if showAttendModal}
  <div class="modal modal-open">
    <div class="modal-box max-w-md">
      <h3 class="font-medium text-xl mb-4">Attend Event</h3>
      <AttendEvent />
      <div class="modal-action">
        <button class="btn btn-sm" onclick={closeAttendModal}>Close</button>
      </div>
    </div>
    <div class="modal-backdrop" onclick={closeAttendModal}></div>
  </div>
{/if}

<!-- Create Event Modal -->
{#if showCreateModal}
  <div class="modal modal-open">
    <div class="modal-box max-w-md">
      <h3 class="font-medium text-xl mb-4">Create Event</h3>
      <CreateEvent />
      <div class="modal-action">
        <button class="btn btn-sm" onclick={closeCreateModal}>Close</button>
      </div>
    </div>
    <div class="modal-backdrop" onclick={closeCreateModal}></div>
  </div>
{/if}

<style>
  .collapsible-container {
    @apply bg-neutral shadow-md border border-accent/20;
    @apply relative overflow-hidden;
  }
  
  .collapse-header {
    @apply flex justify-between items-center cursor-pointer;
  }
  
  .hover-link {
    @apply hover:underline;
  }

  /* Modal backdrop */
  .modal-backdrop {
    @apply fixed inset-0 bg-black/50 z-40;
  }
</style>