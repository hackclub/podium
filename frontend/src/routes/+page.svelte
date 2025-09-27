<svelte:options runes />

<script lang="ts">
  import CreateProject from "$lib/components/CreateProject.svelte";
  import AttendEvent from "$lib/components/AttendEvent.svelte";
  import { getAuthenticatedUser, signOut } from "$lib/user.svelte";
  import UpdateUser from "$lib/components/UpdateUser.svelte";

  import { onMount } from "svelte";
  import { EventsService, ProjectsService } from "$lib/client/sdk.gen";
  import type { PrivateProject, UserEvents } from "$lib/client";
  import { handleError } from "$lib/misc";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { fade } from "svelte/transition";
  import StartWizard from "$lib/components/StartWizard.svelte";
  import DaydreamWizard from "$lib/components/DaydreamWizard.svelte";

  let projects = $state() as Array<PrivateProject>;
  let daydreams = $state([]) as any[];

  onMount(async () => {
    try {
      const { data, error } = await EventsService.getAttendingEventsEventsGet({
        throwOnError: false,
      });
      if (error || !data) return;
      const attending = (data.attending_events ?? []) as any[];
      daydreams = attending.filter((e) =>
        (e.feature_flags_list as string[]).includes("daydream"),
      );

      // Fetch user's projects
      const { data: projectsData, error: projectsError } =
        await ProjectsService.getProjectsProjectsMineGet({
          throwOnError: false,
        });
      if (projectsError || !projectsData) return;
      projects = projectsData;
    } catch (_) {}
  });
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
      {#if daydreams.length}
        <DaydreamWizard {daydreams} {projects} />
      {:else}
        <StartWizard />
      {/if}
    </div>
  </div>
{/if}
