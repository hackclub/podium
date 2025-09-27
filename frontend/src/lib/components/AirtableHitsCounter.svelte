<script lang="ts">
  import { getAirtableHits } from "$lib/airtable-hits.svelte";

  // Check if we're in development (localhost or IP address) or localStorage flag is set
  const isDev = $derived.by(() => {
    if (import.meta.env.DEV) return true;

    // Check localStorage flag
    if (localStorage.getItem("show_airtable_count") === "true") return true;
  });

  const hits = $derived(getAirtableHits());
</script>

{#if isDev}
  <div
    class="fixed top-4 right-4 z-40 px-3 py-2 rounded-lg text-xs font-mono
           bg-base-200/50 text-base-content/40 border border-base-content/10
           transition-all duration-200 hover:bg-base-200 hover:text-base-content
           hover:border-base-content/30 cursor-help select-none"
    title="Airtable API hits for this page render"
  >
    API: {hits}
  </div>
{/if}
