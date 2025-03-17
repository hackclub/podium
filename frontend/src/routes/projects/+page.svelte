<script lang="ts">
  import UpdateProject from "$lib/components/UpdateProject.svelte";
  import JoinProject from "$lib/components/JoinProject.svelte";
  import CreateProject from "$lib/components/CreateProject.svelte";
  import type { PageData } from "./$types";
  import Icon from "@iconify/svelte";
  
  let { data }: { data: PageData } = $props();
  
  let showCreateModal = $state(false);
  let showJoinModal = $state(false);
  let showUpdateModal = $state(false);
  let projectsExpanded = $state(true);
  
  function toggleProjects() {
    const element = document.getElementById('your-projects');
    if (element) {
      element.classList.toggle('hidden');
      projectsExpanded = !projectsExpanded;
    }
  }
  
  function openCreateModal() {
    showCreateModal = true;
  }
  
  function closeCreateModal() {
    showCreateModal = false;
  }
  
  function openJoinModal() {
    showJoinModal = true;
  }
  
  function closeJoinModal() {
    showJoinModal = false;
  }
  
  function openUpdateModal() {
    showUpdateModal = true;
  }
  
  function closeUpdateModal() {
    showUpdateModal = false;
  }
</script>

<div class="max-w-6xl mx-auto py-8 px-6">
  <section class="mb-8 text-center">
    <h1 class="text-3xl font-medium mb-3">Projects Dashboard</h1>
    <p class="text-lg opacity-80 max-w-2xl mx-auto">
      Manage your hackathon projects, collaborate with teammates, and showcase your work.
    </p>
  </section>
  
  <div class="grid gap-8">
    <!-- Your Projects Section -->
    <div class="collapsible-container p-6 rounded-lg">
      <div class="collapse-header" onclick={toggleProjects}>
        <h2 class="text-xl font-medium">Your projects</h2>
        <Icon icon={projectsExpanded ? "mdi:chevron-up" : "mdi:chevron-down"} style="font-size: 24px;" />
      </div>
      <div id="your-projects" class="mt-4">
        <div class="overflow-x-auto">
          <table class="table table-lg w-full table-zebra">
            <thead>
              <tr>
                <th class="text-base">Project Name</th>
                <th class="text-base">Join Code</th>
                <th class="text-base">Description</th>
                <th class="text-base">Repository</th>
                <th class="text-base">Demo</th>
              </tr>
            </thead>
            <tbody>
              {#each data.projects as project}
                <tr>
                  <td class="font-medium">{project.name}</td>
                  <td>
                    <a
                      href={`/projects/?join_code=${project.join_code}`}
                      data-sveltekit-noscroll class="hover-link font-mono text-accent/90 hover:text-accent transition-colors">{project.join_code}</a>
                  </td>
                  <td>{project.description}</td>
                  <td>
                    <a
                      href={project.repo}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-sveltekit-noscroll class="hover-link text-accent hover:text-accent/80 transition-colors">{project.repo}</a>
                  </td>
                  <td>
                    <a
                      href={project.demo}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-sveltekit-noscroll class="hover-link text-accent hover:text-accent/80 transition-colors">{project.demo}</a>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- Action Buttons -->
    <div class="flex justify-center gap-4 mt-4">
      <button class="btn btn-info" onclick={openCreateModal}>
        <Icon icon="icons8:plus" style="font-size: 24px;" />
        Create Project
      </button>
      <button class="btn btn-info" onclick={openJoinModal}>
        <Icon icon="mdi:heart" style="font-size: 24px;" />
        Join Project
      </button>
      <button class="btn btn-info" onclick={openUpdateModal}>
        <Icon icon="radix-icons:update" style="font-size: 24px;" />
        Update Project
      </button>
    </div>
  </div>
</div>

<!-- Create Project Modal -->
{#if showCreateModal}
  <div class="modal modal-open">
    <div class="modal-box max-w-md">
      <h3 class="font-medium text-xl mb-4">Create a Project</h3>
      <CreateProject />
      <div class="modal-action">
        <button class="btn btn-sm" onclick={closeCreateModal}>Close</button>
      </div>
    </div>
    <div class="modal-backdrop" onclick={closeCreateModal}></div>
  </div>
{/if}

<!-- Join Project Modal -->
{#if showJoinModal}
  <div class="modal modal-open">
    <div class="modal-box max-w-md">
      <h3 class="font-medium text-xl mb-4">Join a Project</h3>
      <JoinProject />
      <div class="modal-action">
        <button class="btn btn-sm" onclick={closeJoinModal}>Close</button>
      </div>
    </div>
    <div class="modal-backdrop" onclick={closeJoinModal}></div>
  </div>
{/if}

<!-- Update Project Modal -->
{#if showUpdateModal}
  <div class="modal modal-open">
    <div class="modal-box max-w-md">
      <h3 class="font-medium text-xl mb-4">Update a Project</h3>
      <UpdateProject projects={data.projects} events={data.events} />
      <div class="modal-action">
        <button class="btn btn-sm" onclick={closeUpdateModal}>Close</button>
      </div>
    </div>
    <div class="modal-backdrop" onclick={closeUpdateModal}></div>
  </div>
{/if}

<style>
  .collapsible-container {
    @apply bg-neutral shadow-md border border-accent/20;
    @apply relative overflow-hidden;
  }
  
  .collapse-header {
    @apply flex justify-between items-center cursor-pointer;
  }
  
  .hover-link {
    @apply hover:underline;
  }
  
  /* Modal backdrop */
  .modal-backdrop {
    @apply fixed inset-0 bg-black/50 z-40;
  }
</style>
