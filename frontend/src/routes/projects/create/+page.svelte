<script lang="ts">
  import CreateProject from "$lib/components/CreateProject.svelte";
</script>

<div class="w-full space-y-6">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">Create Project</h1>
    <p class="text-base-content/70">Start a new project for hackathon judging.</p>
  </div>

  <div class="card bg-base-100 shadow-lg w-full">
    <div class="card-body">
      <CreateProject />
    </div>
  </div>
</div>
