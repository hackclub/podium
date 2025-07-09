<script lang="ts">
  import CreateEvent from "$lib/components/CreateEvent.svelte";
</script>

<div class="max-w-2xl mx-auto space-y-6">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">Create Event</h1>
    <p class="text-base-content/70">Start a new hackathon event and invite participants.</p>
  </div>

  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <CreateEvent />
    </div>
  </div>
</div>
