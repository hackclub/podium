<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { on } from "svelte/events";
  console.log(page);
</script>

<div class="flex my-4 flex-col items-center space-y-4">
  {#if page.status == 401}
    <p>Authentication required</p>
    <button
      class="btn btn-primary"
      onclick={() => {
        // Include the current path and search params in the redirect
        goto(`/login?redirect=${encodeURIComponent(page.url.pathname + page.url.search)}`);
      }}
    >
      Login / Sign up
    </button>
  {:else}
    <h1>Error {page.status ?? "Unknown error code"}</h1>
    <h1>{page.error?.message ?? "Unknown error message"}</h1>
  {/if}
</div>
