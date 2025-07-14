<svelte:options runes />

<script lang="ts">
  import CreateProject from "$lib/components/CreateProject.svelte";
  import AttendEvent from "$lib/components/AttendEvent.svelte";
  import { getAuthenticatedUser, signOut } from "$lib/user.svelte";
  import UpdateUser from "$lib/components/UpdateUser.svelte";

  import { onMount } from "svelte";
  import { ProjectsService } from "$lib/client/sdk.gen";
  import type { PrivateProject } from "$lib/client";
  import { handleError } from "$lib/misc";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { fade } from "svelte/transition";
    import StartWizard from "$lib/components/StartWizard.svelte";

  let projects = $state() as Array<PrivateProject>;

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
    </div>

    <StartWizard />

    <!-- User Info Card -->
    <div class="card bg-base-100 shadow-lg">
      <div class="card-body">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div class="w-full">
            <h2 class="text-xl font-semibold">Account</h2>
            <p class="text-base-content/70">
              Signed in as <strong>{getAuthenticatedUser().user.email}</strong>
            </p>
            <p class="text-base-content/70">
              Display name: <strong>{getAuthenticatedUser().user.display_name || `${getAuthenticatedUser().user.first_name} ${getAuthenticatedUser().user.last_name?.[0] || ''}`}</strong>
            </p>
          </div>
          <div class="flex gap-2 w-full sm:w-auto justify-end">
            <UpdateUser user={getAuthenticatedUser().user} />
            <button class="btn btn-outline btn-sm" onclick={signOut}>Sign out</button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}
