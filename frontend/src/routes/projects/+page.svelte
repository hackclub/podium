<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
  import Collapse from "$lib/components/Collapse.svelte";
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  let { data }: { data: PageData } = $props();
</script>

<div class="p-4 mx-auto space-y-4">
  <section>
    <Collapse title="Your projects">
      <div class="overflow-x-auto">
        <table class="table w-full table-zebra">
          <thead>
            <tr>
              <th>Project</th>
              <th>Join Code</th>
            </tr>
          </thead>
          <tbody>
            {#each data.projects as project}
              <tr>
                <td class="w-1/2">
                  <!-- container to make the card smaller -->
                  <div>
                    <ProjectCard
                      {project}
                      isSelected={false}
                      toggle={() => {}}
                      selectable={false}
                    />
                  </div>
                </td>
                <td>
                  <a
                    href={`/projects/?join_code=${project.join_code}`}
                    data-sveltekit-noscroll
                    class="hover-link"
                  >
                    {project.join_code}
                  </a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </Collapse>
  </section>
  <section>
    <Collapse title="Create a project">
      <CreateProject />
    </Collapse>
  </section>
  <section>
    <Collapse title="Join a project">
      <JoinProject />
    </Collapse>
  </section>
  <section>
    <Collapse title="Update a project">
      <UpdateProject projects={data.projects} events={data.events} />
    </Collapse>
  </section>
</div>

<style>
  /* section {
    @apply p-6 rounded-lg shadow-xs border-accent/50 border-2 border-dotted;
  } */
</style>
