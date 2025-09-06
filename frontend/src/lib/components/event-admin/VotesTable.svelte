<script lang="ts">
  import type { Vote } from '$lib/client/types.gen';

  interface Props {
    votes: Vote[];
    voterLookup: Map<string, string>;
    projectLookup: Map<string, string>;
  }

  let { votes, voterLookup, projectLookup }: Props = $props();
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
                  <div class="font-medium">{voterLookup.get(vote.voter[0]) || 'Unknown User'}</div>
                  <div class="text-xs text-base-content/70 font-mono">{vote.voter[0]}</div>
                </td>
                <td>
                  <div class="font-medium">{projectLookup.get(vote.project[0]) || 'Unknown Project'}</div>
                  <div class="text-xs text-base-content/70 font-mono">{vote.project[0]}</div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
