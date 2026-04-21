<script lang="ts">
  import { onMount } from "svelte";
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { ProjectPrivate, EventPublic } from "$lib/client";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  import EventSelector from "$lib/components/EventSelector.svelte";
  import ProjectSubmissionWizard from "$lib/components/ProjectSubmissionWizard.svelte";
  import { setHasProject } from "$lib/project-state.svelte";

  let officialEvents = $state<EventPublic[]>([]);
  let projects = $state<ProjectPrivate[]>([]);
  let attendingEvents = $state<EventPublic[]>([]);
  let loading = $state(true);

  // Only consider events the user is enrolled in AND are currently official
  const activeAttendingEvents = $derived(() => {
    const officialIds = new Set(officialEvents.map((e) => e.id));
    return attendingEvents.filter((e) => officialIds.has(e.id));
  });

  const currentEvent = $derived(() => activeAttendingEvents()[0]);

  // Keep global project state in sync
  $effect(() => {
    setHasProject(projects.length > 0);
  });

  onMount(async () => {
    const user = getAuthenticatedUser();

    // Always load official events — the home page is the event browser
    const officialRes = await EventsService.listOfficialEventsEventsOfficialGet({
      throwOnError: false,
    });
    if (!officialRes.error && officialRes.data) {
      officialEvents = officialRes.data as EventPublic[];
    }

    if (user.access_token) {
      try {
        const [attendingRes, projectsRes] = await Promise.all([
          EventsService.getAttendingEventsEventsGet({ throwOnError: false }),
          ProjectsService.getProjectsProjectsMineGet({ throwOnError: false }),
        ]);

        if (!attendingRes.error && attendingRes.data) {
          attendingEvents = (attendingRes.data.attending_events ??
            []) as EventPublic[];
        }

        if (!projectsRes.error && projectsRes.data) {
          projects = projectsRes.data;
        }
      } catch (err) {
        console.error("Failed to load user data:", err);
      }
    }

    loading = false;
  });

  function handleEventJoined() {
    window.location.reload();
  }

  // Slug → hero image URL for events that have branded artwork
  const eventHeroImages: Record<string, string> = {
    sleepover: "https://wsrv.nl/?url=sleepover.hackclub.com/background/sleepover_logo.PNG&output=webp&h=288&fit=contain",
  };

  // Human-readable phase labels and badge styles
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
</script>

{#if !getAuthenticatedUser().access_token}
  <!-- Unauthenticated: event-first landing — no login wall -->
  <div class="max-w-6xl mx-auto space-y-10">
    <!-- Hero -->
    <div class="flex flex-col items-center text-center gap-4 py-8">
      <img src="/favicon.svg" alt="Podium" class="w-16 h-16" />
      <div>
        <h1 class="text-5xl font-bold text-base-content">Podium</h1>
        <p class="text-base-content/60 mt-2 text-lg">
          Hack Club's peer-judging platform for hackathons
        </p>
      </div>
      <a href="/login" class="btn btn-primary btn-lg mt-2">Sign in to participate</a>
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>
    {:else if officialEvents.length === 1}
      <!-- Single featured event — show as a prominent hero card -->
      <div class="flex justify-center">
        <a
          href={`/events/${officialEvents[0].slug}`}
          class="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md hover:border-primary/30 transition-all group w-full max-w-lg"
        >
          {#if eventHeroImages[officialEvents[0].slug]}
            <figure class="px-10 pt-8 pb-2">
              <img
                src={eventHeroImages[officialEvents[0].slug]}
                alt={officialEvents[0].name}
                class="h-36 object-contain"
              />
            </figure>
          {/if}
          <div class="card-body gap-4 items-center text-center">
            <div class="flex flex-col items-center gap-2">
              <span class="badge {phaseBadge[officialEvents[0].phase] ?? 'badge-ghost'} text-xs">
                {phaseLabel[officialEvents[0].phase] ?? officialEvents[0].phase}
              </span>
              <h2 class="card-title text-2xl group-hover:text-primary transition-colors">
                {officialEvents[0].name}
              </h2>
            </div>
            {#if officialEvents[0].description}
              <p class="text-base-content/60 text-sm">
                {officialEvents[0].description}
              </p>
            {/if}
            <div class="card-actions mt-2">
              <span class="btn btn-primary btn-sm">View event →</span>
            </div>
          </div>
        </a>
      </div>
    {:else if officialEvents.length > 1}
      <!-- Divider with label -->
      <div class="divider text-base-content/40 text-sm font-medium">
        {officialEvents.length} events
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each officialEvents as event (event.id)}
          <a
            href={`/events/${event.slug}`}
            class="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md hover:border-primary/30 transition-all group"
          >
            <div class="card-body gap-3">
              <div class="flex items-start justify-between gap-2">
                <h2 class="card-title text-base group-hover:text-primary transition-colors">
                  {event.name}
                </h2>
                <span
                  class="badge {phaseBadge[event.phase] ?? 'badge-ghost'} shrink-0 text-xs"
                >
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
  </div>
{:else}
  <!-- Authenticated dashboard -->
  <div class="max-w-6xl mx-auto space-y-8" id="home">
    <div id="welcome-back">
      <h1 class="text-3xl font-bold text-base-content mb-2">
        Welcome back, {getAuthenticatedUser().user.first_name}!
      </h1>
    </div>

    <div class="min-h-[60vh] flex items-center justify-center">
      {#if loading}
        <div class="flex flex-col items-center gap-4">
          <span class="loading loading-spinner loading-lg text-primary"></span>
          <p class="text-base-content/70">Loading...</p>
        </div>
      {:else if !currentEvent()}
        <!-- Attending no event yet — pick one -->
        <div class="max-w-md w-full mx-auto">
          <div class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <EventSelector onEventJoined={handleEventJoined} />
            </div>
          </div>
        </div>
      {:else}
        <!-- Attending an event — submit/manage project -->
        <ProjectSubmissionWizard
          flagshipEvents={activeAttendingEvents() as any}
          {projects}
        />
      {/if}
    </div>
  </div>
{/if}
