<script lang="ts">
  import DOMPurify from "dompurify";
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
  import Collapse from "$lib/components/Collapse.svelte";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import { onMount } from "svelte";
  import { ProjectsService } from "$lib/client/sdk.gen";
  import type { Results } from "$lib/client/types.gen";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  let { data }: { data: PageData } = $props();
</script>

<div class="max-w-6xl mx-auto space-y-8">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">
      Hello, {getAuthenticatedUser().user.first_name}!
    </h1>
    <p class="text-base-content/70">Welcome to your profile page. Here you can view all your projects and manage your account.</p>
  </div>

  <!-- User Info Card -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">Profile Information</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div class="label">
            <span class="label-text font-semibold">First Name</span>
          </div>
          <div class="input input-bordered w-full bg-base-200">
            {getAuthenticatedUser().user.first_name}
          </div>
        </div>
        <div>
          <div class="label">
            <span class="label-text font-semibold">Last Name</span>
          </div>
          <div class="input input-bordered w-full bg-base-200">
            {getAuthenticatedUser().user.last_name}
          </div>
        </div>
        <div class="md:col-span-2">
          <div class="label">
            <span class="label-text font-semibold">Email</span>
          </div>
          <div class="input input-bordered w-full bg-base-200">
            {getAuthenticatedUser().user.email}
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Projects Section -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <div class="flex items-center justify-between mb-6">
        <h2 class="card-title text-xl">Your Projects</h2>
        <div class="flex gap-2">
          <a href="/projects/create" class="btn btn-primary btn-sm">Create Project</a>
          <a href="/projects/join" class="btn btn-outline btn-sm">Join Project</a>
        </div>
      </div>
      
      {#if data.projects.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {#each data.projects as project}
            <ProjectCard
              {project}
              isSelected={false}
              toggle={() => {}}
              selectable={false}
            />
          {/each}
        </div>
      {:else}
        <div class="text-center py-8">
          <p class="text-base-content/70 mb-4">You haven't created any projects yet.</p>
          <div class="flex gap-2 justify-center">
            <a href="/projects/create" class="btn btn-primary">Create Your First Project</a>
            <a href="/projects/join" class="btn btn-outline">Join a Project</a>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
