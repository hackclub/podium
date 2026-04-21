<script lang="ts">
  let { children, data } = $props();

  // TEMPORARY: remove this block when Sleepover is over
  const eventHeroImages: Record<string, string> = {
    sleepover: "https://sleepover.hackclub.com/background/sleepover_logo.PNG",
  };
  // END TEMPORARY
</script>

<!-- TEMPORARY: remove this block when Sleepover is over -->
{#if eventHeroImages[data.event.slug]}
  <div class="flex justify-center pt-6 pb-2">
    <img
      src={eventHeroImages[data.event.slug]}
      alt={data.event.name}
      class="h-28 object-contain"
    />
  </div>
{/if}
<!-- END TEMPORARY -->

<div class="text-center p-4">
  <h1 class="text-2xl font-semibold">
    <a href="/events/{data.event.slug}" class="link hover-link">
      {data.event.name}
    </a>
  </h1>
  <p class="text-accent">{data.event.description}</p>
</div>

{@render children()}
