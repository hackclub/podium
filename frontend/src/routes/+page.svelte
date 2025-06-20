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

<div
  class="space-y-8 p-4 max-w-2xl mx-auto flex flex-col justify-center min-h-screen"
>
  <section>
    <h2 class="text-xl font-semibold mb-4">Login</h2>
    {#if getAuthenticatedUser().access_token}
      <div class="my-4 text-center">
        <h2>Hey!</h2>
        <p>
          You're signed in as <strong
            >{getAuthenticatedUser().user.email}</strong
          >.
        </p>
        <!--  Div that stacks the buttons below -->
        <!-- <div class="flex flex-col items-center space-y-2"> -->
        <button class="btn btn-primary mt-2" onclick={signOut}>Sign out</button>
        <!-- <a href="/user" class="btn btn-primary">Profile</a> -->
        <!-- </div>   -->
      </div>
    {:else}
      <div class="flex justify-center my-4">
        <a href="/login" class="btn btn-primary">Login / Sign Up</a>
      </div>
    {/if}
  </section>

  {#if getAuthenticatedUser().access_token}
    <!-- Style and center -->
    <!-- <section>
      <h2 class="text-xl font-semibold mb-4">Events</h2>
      <div class="flex justify-center">
        <a href="/events" class="btn btn-wide btn-primary">
          Events Dashboard
        </a>
      </div>
    </section>
    <section>
      <h2 class="text-xl font-semibold mb-4">Projects</h2>
      <div class="flex justify-center">
        <a href="/projects" class="btn btn-wide btn-primary">
          Projects Dashboard
        </a>
      </div>
    </section> -->
    <!-- <section>
      <h2 class="text-xl font-semibold mb-4">Your profile</h2>
      <div class="flex justify-center">
        <a href="/user" class="btn btn-wide btn-primary">
          Profile
        </a>
      </div>
    </section> -->

    {#if projects}
        <p class="text-center text-lg font-semibold" transition:fade>Your projects</p>
        <div
          class="carousel carousel-vertical rounded-box max-w-3/4 lg:carousel-horizontal mx-auto"
          transition:fade
        >
          {#each projects as project}
            <div class="carousel-item w-full">
              <!-- <img
            src={project.image_url}
            class="w-full"
            alt="{project.name} project image"
          /> -->
              <ProjectCard
                {project}
                isSelected={false}
                toggle={() => {}}
                selectable={false}
              />
            </div>
          {/each}
        </div>
    {/if}
  {/if}
</div>

<style>
  @reference "../app.css";

  section {
    /* @apply p-6 rounded-lg shadow-xs border-accent/50 border-2 border-dotted; */
    @apply p-6 rounded-3xl shadow-2xl ring-2 ring-accent border-accent/10 border-2 border-dotted bg-neutral;
  }

  * {
    @apply text-neutral-content;
  }
</style>
