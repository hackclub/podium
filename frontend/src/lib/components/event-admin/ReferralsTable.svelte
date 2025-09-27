<script lang="ts">
  import type { Referral } from "$lib/client/types.gen";

  interface Props {
    referrals: Referral[];
    userLookup: Map<string, string>;
  }

  let { referrals, userLookup }: Props = $props();
</script>

<div class="card bg-base-200">
  <div class="card-body">
    <h2 class="card-title">Event Referrals ({referrals.length})</h2>

    {#if referrals.length === 0}
      <p class="text-base-content/70">No referrals yet.</p>
    {:else}
      <div class="overflow-x-auto">
        <table class="table table-zebra w-full">
          <thead>
            <tr>
              <th>User</th>
              <th>Referral Source</th>
            </tr>
          </thead>
          <tbody>
            {#each referrals as referral}
              <tr>
                <td>
                  <div class="font-medium">
                    {userLookup.get(referral.user[0]) || "Unknown User"}
                  </div>
                  <div class="text-xs text-base-content/70 font-mono">
                    {referral.user[0]}
                  </div>
                </td>
                <td>
                  <div class="font-medium">
                    {referral.content || "No referral source provided"}
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
