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

  const currentEvent = $derived(() => attendingEvents[0]);

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
      } catch (_) {}
    }

    loading = false;
  });

  function handleEventJoined() {
    window.location.reload();
  }

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
  <!-- Unauthenticated: show public event list — no login wall -->
  <div class="max-w-6xl mx-auto space-y-8">
    <div class="text-center py-4">
      <h1 class="text-4xl font-bold text-base-content mb-2">Podium</h1>
      <p class="text-base-content/70">
        Hack Club's peer-judging platform for hackathons
      </p>
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>
    {:else if officialEvents.length > 0}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each officialEvents as event (event.id)}
          <a
            href={`/events/${event.slug}`}
            class="card bg-base-100 shadow-md hover:shadow-lg transition-shadow"
          >
            <div class="card-body">
              <div class="flex items-start justify-between gap-2">
                <h2 class="card-title text-base">{event.name}</h2>
                <span
                  class="badge {phaseBadge[event.phase] ?? 'badge-ghost'} shrink-0"
                >
                  {phaseLabel[event.phase] ?? event.phase}
                </span>
              </div>
              {#if event.description}
                <p class="text-base-content/70 text-sm line-clamp-2">
                  {event.description}
                </p>
              {/if}
            </div>
          </a>
        {/each}
      </div>
    {:else}
      <p class="text-center text-base-content/70 py-8">
        No events available right now.
      </p>
    {/if}

    <div class="flex justify-center pt-2 pb-8">
      <a href="/login" class="btn btn-primary">Sign in to participate</a>
    </div>
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
          flagshipEvents={attendingEvents as any}
          {projects}
        />
      {/if}
    </div>
  </div>
{/if}
