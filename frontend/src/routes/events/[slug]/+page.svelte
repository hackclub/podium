<script lang="ts">
  import type { PageData } from "./$types";
  import AdminPanel from "$lib/components/event-admin/AdminPanel.svelte";
  import type { EventPrivate } from "$lib/client/types.gen";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  import { toast } from "svelte-sonner";
  import { handleError } from "$lib/misc";
  import { client } from "$lib/client/sdk.gen";
  import { goto } from "$app/navigation";

  let { data }: { data: PageData } = $props();

  let joining = $state(false);

  // Type assertion: owned events are always PrivateEvent
  function getPrivateEvent(
    event: any,
  ): EventPrivate & { owned: boolean; partOfEvent: boolean } {
    return event as EventPrivate & { owned: boolean; partOfEvent: boolean };
  }

  async function joinEvent() {
    joining = true;
    try {
      const response = await client.post<{ message: string; event_id: string }>(
        { url: `/events/${data.event.id}/attend` },
      );
      if (response.error) {
        handleError(response.error);
        return;
      }
      toast.success("Joined event!");
      // Go to home so the user can submit their project
      await goto("/");
    } catch (err) {
      handleError(err);
    } finally {
      joining = false;
    }
  }

  const isAuthenticated = $derived(!!getAuthenticatedUser().access_token);
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
    <div class="divider"></div>
    <div class="card bg-base-200 text-center">
      <div class="card-body gap-2 py-4">
        {#if isAuthenticated}
          <!-- Authenticated but not attending: let them join inline -->
          <p class="text-base-content/70 text-sm">
            You're not attending this event yet.
          </p>
          <button
            class="btn btn-primary btn-sm"
            onclick={joinEvent}
            disabled={joining}
          >
            {#if joining}
              <span class="loading loading-spinner loading-xs"></span>
            {/if}
            Join this event
          </button>
        {:else}
          <!-- Unauthenticated: redirect to login with return URL -->
          <p class="text-base-content/70 text-sm">
            Want to submit a project or vote?
          </p>
          <a
            href="/login?redirect=/events/{data.event.slug}"
            class="btn btn-primary btn-sm"
          >
            Sign in to participate
          </a>
        {/if}
      </div>
    </div>
  {/if}
</div>

{#if data.event.owned}
  <AdminPanel event={getPrivateEvent(data.event)} />
{/if}
