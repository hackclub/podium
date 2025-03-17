<script lang="ts">
    import { user } from "$lib/user.svelte";
  import type { PageData } from "./$types";
  import Icon from "@iconify/svelte";
  
  let { data }: { data: PageData } = $props();
</script>

<div class="max-w-4xl mx-auto py-8 px-6">
  <header class="mb-8 text-center">
    <h1 class="text-3xl font-medium mb-3">{data.event.name}</h1>
    <p class="text-lg opacity-80 max-w-2xl mx-auto">
      {data.event.description || "No description provided"}
    </p>
  </header>

  <div class="grid gap-8 md:grid-cols-2">
    <!-- Event Details -->
    <div class="collapsible-container p-6 rounded-lg">
      <h2 class="text-xl font-medium mb-4">Event Details</h2>
      <div class="space-y-4">
        <div class="flex items-center">
          <Icon icon="mdi:calendar" style="font-size: 24px;" class="mr-3 text-accent" />
          <div>
            <p class="font-medium">Event ID</p>
            <p class="text-accent font-mono">{data.event.id}</p>
          </div>
        </div>
        
        <div class="flex items-center">
          <Icon icon="mdi:account-group" style="font-size: 24px;" class="mr-3 text-accent" />
          <div>
            <p class="font-medium">Status</p>
            <p>{data.event.votable ? "Voting Open" : "Voting Closed"}</p>
          </div>
        </div>
        
        <div class="flex items-center">
          <Icon icon="mdi:information" style="font-size: 24px;" class="mr-3 text-accent" />
          <div>
            <p class="font-medium">Participation</p>
            <p>{data.event.partOfEvent ? "You are participating" : "You are not participating"}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="collapsible-container p-6 rounded-lg">
      <h2 class="text-xl font-medium mb-4">Actions</h2>
      <div class="space-y-4">
        {#if data.event.partOfEvent}
          <a href={`/events/${data.event.id}/rank`} class="btn btn-info w-full flex items-center justify-center">
            <Icon icon="mdi:star" style="font-size: 24px;" class="mr-2" />
            Rank Projects
          </a>
        {/if}
        
        <a href={`/events/${data.event.id}/leaderboard`} class="btn btn-info w-full flex items-center justify-center">
          <Icon icon="mdi:trophy" style="font-size: 24px;" class="mr-2" />
          View Leaderboard
        </a>
        
        <a href="/events" class="btn btn-outline w-full flex items-center justify-center mt-4">
          <Icon icon="mdi:arrow-left" style="font-size: 24px;" class="mr-2" />
          Back to Events
        </a>
      </div>
    </div>
  </div>
</div>

<style>
  .collapsible-container {
    @apply bg-neutral shadow-md border border-accent/20;
    @apply relative overflow-hidden;
  }
</style>
