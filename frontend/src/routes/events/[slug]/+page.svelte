<script lang="ts">
  import type { PageData } from "./$types";
  import AdminPanel from '$lib/components/event-admin/AdminPanel.svelte';

  let { data }: { data: PageData } = $props();
</script>

<div class="flex justify-center flex-col mx-auto max-w-md space-y-4 mt-4">
  {#if data.event.partOfEvent}
    <div
      class="tooltip"
      data-tip={data.event.votable
        ? "Vote for your favorite projects"
        : "You can't vote yet! If you think you should be able to, contact your event organizer."}
    >
      <a
        href={`/events/${data.event.slug}/rank`}
        class="btn-primary btn btn-block {data.event.votable
          ? ''
          : 'btn-disabled'}">Rank Projects</a
      >
    </div>
  {/if}
  {#if !data.event.owned}
    <div
      class="tooltip"
      data-tip={data.event.leaderboard_enabled
        ? "View the leaderboard"
        : "The event organizer has not enabled the leaderboard yet."}
    >
      <a
        href={`/events/${data.event.slug}/leaderboard`}
        class="btn-primary btn btn-block {data.event.leaderboard_enabled
          ? ''
          : 'btn-disabled'}">Leaderboard</a
      >
    </div>
  {/if}
</div>

<AdminPanel event={data.event} />
