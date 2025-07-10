<svelte:options runes />

<script lang="ts">
  import CreateProject from "$lib/components/CreateProject.svelte";
  import AttendEvent from "$lib/components/AttendEvent.svelte";
  import { getAuthenticatedUser, signOut } from "$lib/user.svelte";

  import { onMount } from "svelte";
  import { ProjectsService } from "$lib/client/sdk.gen";
  import type { PrivateProject } from "$lib/client";
  import { handleError } from "$lib/misc";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { fade } from "svelte/transition";

  let projects = $state() as Array<PrivateProject>;

  onMount(async () => {
    // If the user is authenticated, get their projects so they can be displayed
    if (getAuthenticatedUser().access_token) {
      const { data: projectsData, error: projectsErr } =
        await ProjectsService.getProjectsProjectsMineGet({
          throwOnError: false,
        });
      if (projectsErr) {
        console.error("Error fetching projects:", projectsErr);
        handleError(projectsErr);
      } else {
        projects = projectsData || [];
      }
    }
  });
</script>

{#if !getAuthenticatedUser().access_token}
  <!-- Not logged in - center everything -->
  <div class="min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <h1 class="text-4xl font-bold text-base-content mb-4">Welcome to Podium</h1>
        <p class="text-base-content/70 mb-8">Hack Club's open-source peer-judging platform for hackathons</p>
        <a href="/login" class="btn btn-primary btn-lg">Login / Sign Up</a>
      </div>
    </div>
  </div>
{:else}
  <!-- Logged in dashboard -->
  <div class="max-w-6xl mx-auto space-y-8">
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-base-content mb-2">
        Welcome back, {getAuthenticatedUser().user.first_name}!
      </h1>
      <p class="text-base-content/70">Here's an overview of your hackathon activity.</p>
    </div>

    <!-- User Info Card -->
    <div class="card bg-base-100 shadow-lg">
      <div class="card-body">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl font-semibold">Account</h2>
            <p class="text-base-content/70">
              Signed in as <strong>{getAuthenticatedUser().user.email}</strong>
            </p>
          </div>
          <div class="flex gap-2">
            <a href="/user" class="btn btn-outline">View Profile</a>
            <button class="btn btn-ghost" onclick={signOut}>Sign out</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <a href="/events/attend" class="card bg-accent text-accent-content shadow-lg hover:shadow-xl transition-shadow">
        <div class="card-body">
          <div class="flex items-center gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
            <div>
              <h3 class="font-semibold">Join Event</h3>
              <p class="text-sm opacity-90">Enter your ~4 digit code</p>
            </div>
          </div>
        </div>
      </a>

      <a href="/projects/create" class="card bg-info text-info-content shadow-lg hover:shadow-xl transition-shadow">
        <div class="card-body">
          <div class="flex items-center gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <div>
              <h3 class="font-semibold">Create Project</h3>
              <p class="text-sm opacity-90">Start building</p>
            </div>
          </div>
        </div>
      </a>
    </div>

    <!-- Recent Projects -->
    {#if projects && projects.length > 0}
      <div class="card bg-base-100 shadow-lg" transition:fade>
        <div class="card-body">
          <div class="flex items-center justify-between mb-4">
            <h2 class="card-title text-xl">Your Recent Projects</h2>
            <a href="/projects" class="btn btn-sm btn-outline">View All / Edit</a>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each projects.slice(0, 3) as project}
              <ProjectCard
                {project}
                isSelected={false}
                toggle={() => {}}
                selectable={false}
              />
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}
