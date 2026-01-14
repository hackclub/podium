<script lang="ts">
  // @ts-ignore
  import { PUBLIC_API_URL } from "$env/static/public";

  const isDev = import.meta.env.DEV;
  const isLocalBackend = PUBLIC_API_URL.includes("localhost") || PUBLIC_API_URL.includes("127.0.0.1");
  const showWarning = isDev && !isLocalBackend;
</script>

{#if showWarning}
  <!-- Red border around viewport -->
  <div
    class="fixed inset-0 pointer-events-none z-[9999] border-4 border-red-500"
    aria-hidden="true"
  ></div>

  <!-- Notice at bottom of screen -->
  <div
    class="fixed bottom-0 left-0 right-0 z-[9998] bg-red-500 text-white text-center py-2 text-sm font-medium"
  >
    ⚠️ Development frontend connected to PRODUCTION backend — The red border is a warning that you're running dev mode against prod.
  </div>
{/if}
