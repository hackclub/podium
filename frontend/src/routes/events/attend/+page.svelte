<script lang="ts">
  import AttendEvent from "$lib/components/AttendEvent.svelte";
</script>

<div class="w-full space-y-6">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">Attend Event</h1>
    <p class="text-base-content/70">
      Join an existing hackathon event using an invite code.
    </p>
  </div>

  <div class="card bg-base-100 shadow-lg w-full">
    <div class="card-body">
      <AttendEvent />
    </div>
  </div>
</div>
