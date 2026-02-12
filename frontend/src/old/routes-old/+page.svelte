<script lang="ts">
  import { onMount } from "svelte";
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { ProjectPrivate, EventPublic } from "$lib/client";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  import EventSelector from "$lib/components/EventSelector.svelte";
  import ProjectSubmissionWizard from "$lib/components/ProjectSubmissionWizard.svelte";
  import { setHasProject } from "$lib/project-state.svelte";

  let projects = $state<ProjectPrivate[]>([]);
  let attendingEvents = $state<EventPublic[]>([]);
  let loading = $state(true);

  const currentEvent = $derived(() => attendingEvents[0]);

  const hasProjectForCurrentEvent = $derived(() => {
    const event = currentEvent();
    if (!event || !projects.length) return false;
    return projects.some((p) => p.event_id === event.id);
  });

  onMount(async () => {
    if (!getAuthenticatedUser().access_token) {
      loading = false;
      return;
    }

    try {
      const [eventsRes, projectsRes] = await Promise.all([
        EventsService.getAttendingEventsEventsGet({ throwOnError: false }),
        ProjectsService.getProjectsProjectsMineGet({ throwOnError: false }),
      ]);

      if (!eventsRes.error && eventsRes.data) {
        attendingEvents = (eventsRes.data.attending_events ??
          []) as EventPublic[];
      }

      if (!projectsRes.error && projectsRes.data) {
        projects = projectsRes.data;
      }

      // Update global project state for sidebar navigation
      setHasProject(projects.length > 0);
    } catch (_) {}

    loading = false;
  });

  function handleEventJoined() {
    window.location.reload();
  }
</script>

{#if !getAuthenticatedUser().access_token}
  <!-- Not logged in - center everything -->
  <div class="flex items-center justify-center">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <h1 class="text-4xl font-bold text-base-content mb-4">
          Welcome to Podium
        </h1>
        <p class="text-base-content/70 mb-8">
          Hack Club's open-source peer-judging platform for hackathons
        </p>
        <a href="/login" class="btn btn-primary btn-lg">Login / Sign Up</a>
      </div>
    </div>
  </div>
{:else}
  <!-- Logged in dashboard -->
  <div class="max-w-6xl mx-auto space-y-8" id="home">
    <div class="mb-8" id="welcome-back">
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
        <!-- User not attending any event - show event selector -->
        <div class="max-w-md w-full mx-auto">
          <div class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <EventSelector onEventJoined={handleEventJoined} />
            </div>
          </div>
        </div>
      {:else}
        <!-- User is attending an event - show project wizard -->
        <ProjectSubmissionWizard
          flagshipEvents={attendingEvents as any}
          {projects}
        />
      {/if}
    </div>
  </div>
{/if}
