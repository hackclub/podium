<script lang="ts">
  import type { PageData } from "./$types";
  import AdminPanel from "$lib/components/event-admin/AdminPanel.svelte";
  import type { EventPrivate } from "$lib/client/types.gen";

  let { data }: { data: PageData } = $props();

  // Type assertion: owned events are always PrivateEvent
  function getPrivateEvent(
    event: any,
  ): EventPrivate & { owned: boolean; partOfEvent: boolean } {
    return event as EventPrivate & { owned: boolean; partOfEvent: boolean };
  }
</script>

<div class="flex justify-center flex-col mx-auto max-w-md space-y-4 mt-4">
  {#if data.event.partOfEvent}
    <div
      class="tooltip"
      data-tip={data.event.phase === "voting"
        ? "Vote for your favorite projects"
        : "You can't vote yet! If you think you should be able to, contact your event organizer."}
    >
      <a
        href={`/events/${data.event.slug}/rank`}
        class="btn-primary btn btn-block {data.event.phase === 'voting'
          ? ''
          : 'btn-disabled'}">Rank Projects</a
      >
    </div>
  {/if}
  {#if !data.event.owned}
    <div
      class="tooltip"
      data-tip={data.event.phase === "closed"
        ? "View the leaderboard"
        : "Results will be available after voting closes."}
    >
      <a
        href={`/events/${data.event.slug}/leaderboard`}
        class="btn-primary btn btn-block {data.event.phase === 'closed'
          ? ''
          : 'btn-disabled'}">Leaderboard</a
      >
    </div>
  {/if}

  {#if !data.event.partOfEvent && !data.event.owned}
    <!-- Visitor: prompt them to sign in and join -->
    <div class="divider"></div>
    <div class="card bg-base-200 text-center">
      <div class="card-body gap-2 py-4">
        <p class="text-base-content/70 text-sm">
          Want to submit a project or vote?
        </p>
        <a href="/login?redirect=/events/{data.event.slug}" class="btn btn-primary btn-sm">
          Sign in to participate
        </a>
      </div>
    </div>
  {/if}
</div>

{#if data.event.owned}
  <AdminPanel event={getPrivateEvent(data.event)} />
{/if}
