<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
import Collapse from "$lib/components/Collapse.svelte";
  let { data }: { data: PageData } = $props();
</script>

<div class="p-4 mx-auto space-y-4">
  <!-- <div > -->
  <section>
    <Collapse title="Your projects">
    <!-- <h2 class="text-xl font-semibold mb-4">Your projects</h2> -->
    <div class="overflow-x-auto">
    <table class="table w-full table-zebra">
      <thead>
        <tr>
          <th>Project Name</th>
          <th>Join Code</th>
          <th>Description</th>
          <th>Repository</th>
          <th>Demo</th>
        </tr>
      </thead>
      <tbody>
        {#each data.projects as project}
          <tr>
            <td>{project.name}</td>
            <td
              ><a
                href={`/projects/?join_code=${project.join_code}`}
                data-sveltekit-noscroll  class="hover-link">{project.join_code}</a
              ></td
            >
            <td>{project.description}</td>
            <td
              ><a
                href={project.repo}
                data-sveltekit-noscroll  class="hover-link">{project.repo}</a
              ></td
            >
            <td
              ><a
                href={project.demo}
                data-sveltekit-noscroll class="hover-link">{project.demo}</a
              ></td>
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
    @apply p-6 rounded-lg shadow-sm border-accent/50 border-2 border-dotted;
  } */
</style>
