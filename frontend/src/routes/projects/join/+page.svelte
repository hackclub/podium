<script lang="ts">
  import JoinProject from "$lib/components/JoinProject.svelte";
</script>

<div class="max-w-2xl mx-auto space-y-6">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">Join Project</h1>
    <p class="text-base-content/70">Join an existing project team using an invite code.</p>
  </div>

  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <JoinProject />
    </div>
  </div>
</div>
