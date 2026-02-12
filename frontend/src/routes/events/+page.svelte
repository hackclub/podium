<script lang="ts">
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();
</script>

<div class="max-w-6xl mx-auto space-y-8">
  <!-- Events you're attending -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">Your Events</h2>
      <p class="text-base-content/70 mb-4">
        Click on an event's name to view the event page, the leaderboard, or to
        vote on projects.
      </p>
      {#if data.events.attending_events.length > 0}
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>Event Name</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {#each data.events.attending_events as event}
                <tr>
                  <td>
                    <a
                      href={`/events/${event.slug}`}
                      class="link link-primary font-medium"
                    >
                      {event.name}
                    </a>
                  </td>
                  <td class="max-w-md">
                    <p class="truncate">{event.description}</p>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="text-center py-8">
          <p class="text-base-content/70 mb-4">
            You're not attending any events yet. Select an event from the
            homepage to get started.
          </p>
          <a href="/" class="btn btn-primary">Go to Homepage</a>
        </div>
      {/if}
    </div>
  </div>
</div>
