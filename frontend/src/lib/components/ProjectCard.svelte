<script lang="ts">
  import { UsersService } from "$lib/client";
  import type { PrivateProject, Project } from "$lib/client/types.gen";
  import { handleError } from "$lib/misc";
  import { onMount } from "svelte";
  interface Props {
    project: PrivateProject | Project;
    isSelected: boolean;
    toggle: () => void;
    selectable?: boolean;
  }
  let credits = $state("");
  let loadingCredits = $state(true);
  let loadingImage = $state(true);

  let { project, isSelected, toggle, selectable = false }: Props = $props();
  onMount(async () => {
    // Merge project.collaborators and project.owner into a single array
    const allUserIds = [
      ...(project.collaborators || []),
      ...(project.owner || []),
    ];
    let names: string[] = [];
    for (const userId of allUserIds) {
      const {
        data,
        error: err,
        response,
      } = await UsersService.getUserPublicUsersUserIdGet({
        path: {
          user_id: userId,
        },
        throwOnError: false,
      });
      if (err) {
        handleError(err);
      } else if (data && data.display_name) {
        names.push(data.display_name);
      }
    }
    
    // Only format if we have valid names
    if (names.length > 0) {
      // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/ListFormat/ListFormat#parameters
      const formatter = new Intl.ListFormat("en", {
        style: "short",
        type: "conjunction",
      });
      credits = formatter.format(names);
    } else {
      credits = "Unknown contributors";
    }
    loadingCredits = false;
  });

  // $inspect(project);
</script>

<button
  type="button"
  onclick={() => {
    if (selectable) {
      console.debug("card clicked");
      toggle();
    }
  }}
  onkeydown={selectable ? (e) => e.key === "Enter" && toggle() : null}
  aria-pressed={isSelected}
  disabled={!selectable}
  class="m-4"
>
  <div
    class="card card-sm bg-base-100 rounded transition-transform duration-200 border-solid border-base {isSelected
      ? 'border-info scale-110 border-2'
      : ''}"
  >
    <figure class="w-full relative">
      <img
        src={project.image_url}
        alt="Project"
        class="object-contain w-full h-auth max-h-48"
        loading="lazy"
        onload={() => (loadingImage = false)}
        onerror={() => (loadingImage = false)}
        style="opacity: {loadingImage ? 0 : 1}; transition: opacity 0.2s;"
      />
      {#if loadingImage}
        <div class="skeleton h-48 w-full absolute top-0 left-0"></div>
      {/if}
    </figure>
    <div class="card-body">
      <h2 class="card-title break-words overflow-x-auto">
        {project.name}
      </h2>
      <div class="divider my-0"></div>
      <p class="break-words text-sm">{project.description}</p>
      {#if loadingCredits}
        <div class="skeleton h-4 w-32"></div>
      {:else}
        <p class="break-words text-xs">{credits}</p>
      {/if}
      <div class="card-actions justify-end mt-2">
        <a href={project.repo} target="_blank" rel="noopener">
          <div class="badge badge-secondary badge-lg underline">Repo</div>
        </a>
        <a href={project.demo} target="_blank" rel="noopener">
          <div class="badge badge-primary badge-lg underline">Demo</div>
        </a>
      </div>
    </div>
  </div>
</button>
