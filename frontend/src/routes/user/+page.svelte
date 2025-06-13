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

<div class="text-center p-4">
  <h1 class="text-2xl font-semibold">
    Hi {getAuthenticatedUser().user.first_name}!
  </h1>
  <p class="text-accent">Here are your projects!</p>
</div>

<div
  class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mx-auto max-w-4xl"
>
  {#each data.projects as project}
    <div class="flex flex-col items-center">
      <ProjectCard
        {project}
        isSelected={false}
        toggle={() => {}}
        selectable={false}
      />
    </div>
  {/each}
</div>
