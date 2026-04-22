<script lang="ts">
  import type { EventPublic } from "$lib/client";

  let {
    events = [],
    loading = false,
    error = false,
  }: {
    events: EventPublic[];
    loading?: boolean;
    error?: boolean;
  } = $props();

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
  const eventHeroImages: Record<string, string> = {
    sleepover: "https://wsrv.nl/?url=sleepover.hackclub.com/background/sleepover_logo.PNG&output=webp&h=288&fit=contain",
  };
</script>

{#if loading}
  <div class="flex justify-center py-12">
    <span class="loading loading-spinner loading-lg text-primary"></span>
  </div>
{:else if error}
  <div class="alert alert-error">
    <span>Failed to load events. Please refresh the page.</span>
  </div>
{:else if events.length === 1}
  <div class="flex justify-center">
    <a
      href={`/events/${events[0].slug}`}
      class="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md hover:border-primary/30 transition-all group w-full max-w-lg"
    >
      {#if eventHeroImages[events[0].slug]}
        <figure class="px-10 pt-8 pb-2">
          <img
            src={eventHeroImages[events[0].slug]}
            alt={events[0].name}
            class="h-36 object-contain"
          />
        </figure>
      {/if}
      <div class="card-body gap-4 items-center text-center">
        <div class="flex flex-col items-center gap-2">
          <span class="badge {phaseBadge[events[0].phase] ?? 'badge-ghost'} text-xs">
            {phaseLabel[events[0].phase] ?? events[0].phase}
          </span>
          <h2 class="card-title text-2xl group-hover:text-primary transition-colors">
            {events[0].name}
          </h2>
        </div>
        {#if events[0].description}
          <p class="text-base-content/60 text-sm">{events[0].description}</p>
        {/if}
        <div class="card-actions mt-2">
          <span class="btn btn-primary btn-sm">View event →</span>
        </div>
      </div>
    </a>
  </div>
{:else if events.length > 1}
  <div class="divider text-base-content/40 text-sm font-medium">
    {events.length} events
  </div>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {#each events as event (event.id)}
      <a
        href={`/events/${event.slug}`}
        class="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md hover:border-primary/30 transition-all group"
      >
        <div class="card-body gap-3">
          <div class="flex items-start justify-between gap-2">
            <h2 class="card-title text-base group-hover:text-primary transition-colors">
              {event.name}
            </h2>
            <span class="badge {phaseBadge[event.phase] ?? 'badge-ghost'} shrink-0 text-xs">
              {phaseLabel[event.phase] ?? event.phase}
            </span>
          </div>
          {#if event.description}
            <p class="text-base-content/60 text-sm line-clamp-2">
              {event.description}
            </p>
          {/if}
          <div class="flex justify-end">
            <span class="text-primary text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
              View event →
            </span>
          </div>
        </div>
      </a>
    {/each}
  </div>
{:else}
  <p class="text-center text-base-content/50 py-8">
    No events available right now. Check back soon.
  </p>
{/if}
