<script lang="ts">
  import type { VoteResponse } from "$lib/client/types.gen";

  interface Props {
    votes: VoteResponse[];
    userLookup: Map<string, string>;
    projectLookup: Map<string, string>;
  }

  let { votes, userLookup, projectLookup }: Props = $props();
</script>

<div class="card bg-base-200">
  <div class="card-body">
    <h2 class="card-title">Event Votes ({votes.length})</h2>

    {#if votes.length === 0}
      <p class="text-base-content/70">No votes yet.</p>
    {:else}
      <div class="overflow-x-auto">
        <table class="table table-zebra w-full">
          <thead>
            <tr>
              <th>Voter</th>
              <th>Project</th>
            </tr>
          </thead>
          <tbody>
            {#each votes as vote}
              <tr>
                <td>
                  <div class="font-medium">
                    {userLookup.get(vote.voter_id) || "Unknown User"}
                  </div>
                  <div class="text-xs text-base-content/70 font-mono">
                    {vote.voter_id}
                  </div>
                </td>
                <td>
                  <div class="font-medium">
                    {projectLookup.get(vote.project_id) || "Unknown Project"}
                  </div>
                  <div class="text-xs text-base-content/70 font-mono">
                    {vote.project_id}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
