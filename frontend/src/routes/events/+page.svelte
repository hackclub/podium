<svelte:options runes />

<script lang="ts">
  import AttendEvent from "$lib/components/AttendEvent.svelte";
  import CreateEvent from "$lib/components/CreateEvent.svelte";
  import { EventsService } from "$lib/client";
  import type { PageData } from "./$types";
  import { handleError } from "$lib/misc";
  import { toast } from "svelte-sonner";
  import Collapse from "$lib/components/Collapse.svelte";

  let { data }: { data: PageData } = $props();

  async function onVotableCheck(value: boolean, eventId: string) {
    try {
      console.log(value, eventId);
      await EventsService.changeVotableEventsChangeVotablePut({
        query: { votable: value },
        path: { event_id: eventId },
        throwOnError: true,
      });
      toast(value ? "Voting is now open." : "Voting is now closed.");
    } catch (err) {
      handleError(err);
    }
  }
</script>

<div class="space-y-8 p-4">
  <section>
    <Collapse title="Events you're attending" expandByDefault>
    <div class="overflow-x-auto">
    <table class="table w-full table-zebra">
      <thead>
        <tr>
          <th>Event Name</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {#each data.events.attending_events as event}
          <tr>
            <td><a href={`/events/${event.id}`} class="hover-link">{event.name}</a></td>
            <td>{event.description}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Collapse>
</section>
<section>
    <Collapse title="Attend Event">
    <AttendEvent />
  </Collapse>
  </section>
  <section>
    <Collapse title="Create Event">
    <CreateEvent />
  </Collapse>
  </section>
  <section>
    <Collapse title="Owned Events">
    <div class="overflow-x-auto">
    <table class="table w-full table-zebra">
      <thead>
        <tr>
          <th>Event Name</th>
          <th>Description</th>
          <th>Join Code</th>
          <th>Votable</th>
        </tr>
      </thead>
      <tbody>
        {#each data.events.owned_events as event}
          <tr>
            <td><a href={`/events/${event.id}`} class="hover-link">{event.name}</a></td>
            <td>{event.description}</td>
            <!-- <span class="ml-4 bg-base-300 p-1 rounded"></span> -->
            <td
              ><a
                href={`/events/?join_code=${event.join_code}`}
                data-sveltekit-noscroll class="hover-link">{event.join_code}</a
              ></td
            >
            <td
              ><input
                type="checkbox"
                class="checkbox"
                checked={event.votable}
                onchange={(e) =>
                  onVotableCheck(
                    (e.target as HTMLInputElement).checked,
                    event.id,
                  )}
              /></td
            >
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  </Collapse>
  </section>
</div>