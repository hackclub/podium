<script lang="ts">
  import { onMount } from "svelte";
  import type { PageData } from "./$types";
  import { EventsService } from "$lib/client/sdk.gen";
  import type { EventPublic } from "$lib/client";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  import OfficialEventsDisplay from "$lib/components/OfficialEventsDisplay.svelte";

  let { data }: { data: PageData } = $props();

  let officialEvents = $state<EventPublic[]>([]);
  let loadingOfficial = $state(true);
  let loadError = $state(false);

  // Phase display helpers for the "Your Events" table
  const phaseLabel: Record<string, string> = {
    draft: "Draft",
    submission: "Submissions Open",
    voting: "Voting Open",
    closed: "Results Available",
  };
  const phaseBadge: Record<string, string> = {
    draft: "badge-ghost",
    submission: "badge-success",
    voting: "badge-warning",
    closed: "badge-info",
  };

  onMount(async () => {
    const res = await EventsService.listOfficialEventsEventsOfficialGet({
      throwOnError: false,
    });
    if (!res.error && res.data) {
      officialEvents = res.data as EventPublic[];
    } else if (res.error) {
      loadError = true;
    }
    loadingOfficial = false;
  });
</script>

<div class="max-w-6xl mx-auto space-y-8">
  {#if getAuthenticatedUser().access_token && data.events.attending_events.length > 0}
    <!-- Authenticated: show the events the user is attending -->
    <div class="card bg-base-100 shadow-lg">
      <div class="card-body">
        <h2 class="card-title text-xl mb-2">Your Events</h2>
        <p class="text-base-content/70 mb-4 text-sm">
          Click an event to view details, vote on projects, or see the
          leaderboard.
        </p>
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>Event Name</th>
                <th>Status</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {#each data.events.attending_events as event (event.id)}
                <tr>
                  <td>
                    <a
                      href={`/events/${event.slug}`}
                      class="link link-primary font-medium"
                    >
                      {event.name}
                    </a>
                  </td>
                  <td>
                    <span
                      class="badge {phaseBadge[event.phase] ?? 'badge-ghost'}"
                    >
                      {phaseLabel[event.phase] ?? event.phase}
                    </span>
                  </td>
                  <td class="max-w-xs">
                    <p class="truncate">{event.description}</p>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  {:else}
    <!-- No attending events (unauthenticated or hasn't joined one) -->
    <div class="text-center py-4">
      <h1 class="text-3xl font-bold text-base-content mb-2">Events</h1>
      {#if !getAuthenticatedUser().access_token}
        <p class="text-base-content/70">
          <a href="/login" class="link link-primary">Sign in</a> to join an event
          and submit your project.
        </p>
      {:else}
        <p class="text-base-content/70">
          You're not attending any events yet. <a href="/" class="link link-primary"
            >Go to the home page</a
          > to join one.
        </p>
      {/if}
    </div>

    <OfficialEventsDisplay events={officialEvents} loading={loadingOfficial} error={loadError} />
  {/if}
</div>
