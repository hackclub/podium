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
    import SignupWizard from "$lib/components/SignupWizard.svelte";

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

    <SignupWizard />

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
            <button class="btn btn-outline" onclick={signOut}>Sign out</button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}
