<script lang="ts">
  import { onMount } from "svelte";
  import type { EventPublic } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import { client } from "$lib/client/sdk.gen";

  interface Props {
    onEventJoined?: () => void;
  }

  let { onEventJoined }: Props = $props();

  let events = $state<EventPublic[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let joiningEventId = $state<string | null>(null);

  const filteredEvents = $derived(() => {
    if (!searchQuery.trim()) return events;
    const query = searchQuery.toLowerCase();
    return events.filter(
      (e) =>
        e.name.toLowerCase().includes(query) ||
        e.description.toLowerCase().includes(query),
    );
  });

  onMount(async () => {
    try {
      const response = await client.get<EventPublic[]>({
        url: "/events/official",
      });
      events = response.data || [];
    } catch (err) {
      console.error("Failed to fetch events:", err);
      handleError(err);
    } finally {
      loading = false;
    }
  });

  async function joinEvent(eventId: string) {
    joiningEventId = eventId;
    try {
      const response = await client.post<{ message: string; event_id: string }>(
        {
          url: `/events/${eventId}/attend`,
        },
      );

      if (response.error) {
        handleError(response.error);
        return;
      }

      toast.success("Joined event successfully!");
      await customInvalidateAll();

      if (onEventJoined) {
        onEventJoined();
      }
    } catch (err) {
      handleError(err);
    } finally {
      joiningEventId = null;
    }
  }
</script>

<div class="w-full">
  <div class="text-center mb-6">
    <h1 class="text-3xl font-bold text-primary mb-2">Select Your Event</h1>
    <p class="text-base-content/70">
      Choose which hackathon location you're at
    </p>
  </div>

  {#if loading}
    <div class="flex justify-center py-8">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>
  {:else if events.length === 0}
    <div class="alert alert-warning">
      <span>No active events at this time. Check back soon!</span>
    </div>
  {:else}
    <div class="space-y-4">
      <label class="input input-bordered flex items-center gap-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 16 16"
          fill="currentColor"
          class="h-4 w-4 opacity-70"
        >
          <path
            fill-rule="evenodd"
            d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
            clip-rule="evenodd"
          />
        </svg>
        <input
          type="text"
          class="grow"
          placeholder="Search events..."
          bind:value={searchQuery}
        />
      </label>

      <div class="grid gap-3 max-h-96 overflow-y-auto">
        {#each filteredEvents() as event (event.id)}
          <button
            class="card bg-base-200 hover:bg-base-300 transition-colors cursor-pointer text-left"
            onclick={() => joinEvent(event.id)}
            disabled={joiningEventId !== null}
          >
            <div class="card-body p-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="font-semibold text-lg">{event.name}</h3>
                  {#if event.description}
                    <p class="text-base-content/70 text-sm">
                      {event.description}
                    </p>
                  {/if}
                </div>
                <div>
                  {#if joiningEventId === event.id}
                    <span class="loading loading-spinner loading-sm"></span>
                  {:else}
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 text-base-content/50"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  {/if}
                </div>
              </div>
            </div>
          </button>
        {/each}
      </div>

      {#if filteredEvents().length === 0 && searchQuery}
        <div class="text-center py-4 text-base-content/70">
          No events match "{searchQuery}"
        </div>
      {/if}
    </div>
  {/if}
</div>
