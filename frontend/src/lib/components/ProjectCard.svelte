<script lang="ts">
  import type { Project } from "$lib/client/types.gen";
  interface Props {
    project: Project;
    isSelected: boolean;
    toggle: () => void;
    selectable?: boolean;
  }

  let { project, isSelected, toggle, selectable = false }: Props = $props();

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
    class="card bg-base-100 card-compact rounded transition-transform duration-200 border-solid border-base {isSelected
      ? 'border-info scale-110 border-2'
      : ''}"
  >
    <figure class="relative w-full aspect-video">
      <img 
        src={project.image_url} 
        alt="Project"
        class="absolute inset-0 w-full h-full object-cover"
        loading="lazy"
      />
    </figure>
    <div class="card-body">
      <h2 class="card-title break-words overflow-x-auto whitespace-nowrap">
        {project.name}
      </h2>
      <p class="break-words text-sm">{project.description}</p>
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
