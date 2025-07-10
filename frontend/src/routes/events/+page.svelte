<svelte:options runes />

<script lang="ts">
  import UpdateEvent from "$lib/components/UpdateEvent.svelte";
  import { EventsService } from "$lib/client";
  import type { PageData } from "./$types";
  import { handleError } from "$lib/misc";
  import { toast } from "svelte-sonner";

  let { data }: { data: PageData } = $props();
</script>

<div class="max-w-6xl mx-auto space-y-8">

  <!-- Events you're attending -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">Events You're Attending</h2>
      {#if data.events.attending_events.length > 0}
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>Event Name</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each data.events.attending_events as event}
                <tr>
                  <td>
                    <a href={`/events/${event.slug}`} class="link link-primary font-medium">
                      {event.name}
                    </a>
                  </td>
                  <td class="max-w-md">
                    <p class="truncate">{event.description}</p>
                  </td>
                  <td>
                    <a href={`/events/${event.slug}`} class="btn btn-sm btn-primary">
                      View Event
                    </a>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="text-center py-8">
          <p class="text-base-content/70 mb-4">You're not attending any events yet.</p>
          <a href="/events/attend" class="btn btn-primary">Attend an Event</a>
        </div>
      {/if}
    </div>
  </div>

  <!-- Owned Events - only show if user has owned events -->
  {#if data.events.owned_events.length > 0}
    <div class="card bg-base-100 shadow-lg">
      <div class="card-body">
        <h2 class="card-title text-xl mb-4">Events You Own</h2>
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>Event Name</th>
                <th>Description</th>
                <th>Join Code</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each data.events.owned_events as event}
                <tr>
                  <td>
                    <a href={`/events/${event.slug}`} class="link link-primary font-medium">
                      {event.name}
                    </a>
                  </td>
                  <td class="max-w-md">
                    <p class="truncate">{event.description}</p>
                  </td>
                  <td>
                    <span class="badge badge-accent font-mono">
                      {event.join_code}
                    </span>
                  </td>
                  <td>
                    <div class="flex gap-2">
                      <a href={`/events/${event.slug}`} class="btn btn-sm btn-primary">
                        View
                      </a>
                      <UpdateEvent
                        preselectedEvent={event}
                        events={data.events.owned_events}
                      />
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  {/if}
</div>
